"""
Text-to-SQL query engine using LangChain SQLDatabaseChain + Groq LLM.
Answers natural language questions about stored transactions.
"""

import logging
import re
from functools import lru_cache
from typing import Optional

# Guard all langchain imports
try:
    from langchain_community.utilities import SQLDatabase
    _HAS_SQL_DATABASE = True
except Exception:
    SQLDatabase = None  # type: ignore
    _HAS_SQL_DATABASE = False

# Guard imports that may not be present depending on installed langchain versions
try:
    from langchain_groq import ChatGroq
    _HAS_GROQ = True
except Exception:
    ChatGroq = None  # type: ignore
    _HAS_GROQ = False

try:
    from langchain_experimental.sql import SQLDatabaseChain
    _HAS_SQL_CHAIN = True
except Exception:
    SQLDatabaseChain = None  # type: ignore
    _HAS_SQL_CHAIN = False

try:
    from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
    _HAS_QUERY_TOOL = True
except Exception:
    QuerySQLDataBaseTool = None  # type: ignore
    _HAS_QUERY_TOOL = False

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Check if text-to-sql is available
TEXT_TO_SQL_AVAILABLE = _HAS_SQL_DATABASE and _HAS_GROQ and _HAS_SQL_CHAIN


def _extract_sql(text: str) -> str:
    """Extract SQL from LLM response."""
    # Strip markdown code blocks
    if "```" in text:
        blocks = re.findall(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if blocks:
            return blocks[0].strip()
    # Look for SELECT statement
    match = re.search(r"(SELECT\s.+)", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


class TextToSQLEngine:
    """Answers natural language questions about transactions using SQL."""

    def __init__(self):
        self._db: Optional[SQLDatabase] = None
        self._llm: Optional[ChatGroq] = None

    def _get_db(self) -> SQLDatabase:
        if self._db is None:
            # Use direct SQLite URL with only the transactions table exposed
            # Include more sample rows to show tax-relevant columns
            self._db = SQLDatabase.from_uri(
                settings.database_url,
                include_tables=["transactions"],
                sample_rows_in_table_info=5,
                view_support=True,
            )
        return self._db

    def _get_llm(self) -> ChatGroq:
        if self._llm is None:
            # Check if API key is configured
            if not settings.groq_api_key or settings.groq_api_key == "your_groq_api_key_here":
                raise ValueError("GROQ_API_KEY is not configured. Please set it in your .env file.")
            self._llm = ChatGroq(
                api_key=settings.groq_api_key,
                model_name=settings.groq_model,
                temperature=0,
            )
        return self._llm

    def query(self, question: str, user_id: int) -> dict:
        """
        Answer a natural language question about the user's transactions.
        Returns: {sql, result, answer}
        """
        try:
            # If required packages aren't available, return a clear message
            if not TEXT_TO_SQL_AVAILABLE:
                missing = []
                if not _HAS_SQL_DATABASE:
                    missing.append("langchain-community (SQLDatabase)")
                if not _HAS_GROQ:
                    missing.append("langchain-groq (ChatGroq)")
                if not _HAS_SQL_CHAIN:
                    missing.append("langchain-experimental (SQLDatabaseChain)")
                
                return {
                    "question": question,
                    "sql": "",
                    "result": "",
                    "answer": f"⚠️ Text-to-SQL is unavailable. Missing packages: {', '.join(missing)}. The application is running in limited mode without LLM query features.",
                }
            
            db = self._get_db()
            llm = self._get_llm()

            # Add user_id context to question for security
            augmented_question = (
                f"{question} "
                f"(Only include transactions where user_id = {user_id}. "
                f"Use Indian Rupee format for monetary amounts.)"
            )

            # Use SQLDatabaseChain with return_intermediate_steps
            sql_chain = SQLDatabaseChain.from_llm(
                llm=llm,
                db=db,
                verbose=True,
                return_intermediate_steps=True,
                return_direct=False
            )
            
            result = sql_chain.invoke(augmented_question)
            
            # Extract SQL and result from the chain output
            clean_sql = ""
            raw_result = None
            answer = result.get("result", "")
            
            # Try to extract from intermediate_steps
            if "intermediate_steps" in result and result["intermediate_steps"]:
                steps = result["intermediate_steps"]
                logger.info(f"Intermediate steps type: {type(steps)}, content: {steps}")
                
                # intermediate_steps is typically a list or dict
                if isinstance(steps, list):
                    for step in steps:
                        if isinstance(step, dict):
                            if "sql_cmd" in step:
                                clean_sql = step["sql_cmd"]
                            if "result" in step:
                                raw_result = step["result"]
                        elif isinstance(step, str):
                            # Sometimes it's just the SQL string
                            if "SELECT" in step.upper():
                                clean_sql = step
                elif isinstance(steps, dict):
                    if "sql_cmd" in steps:
                        clean_sql = steps["sql_cmd"]
                    if "result" in steps:
                        raw_result = steps["result"]
            
            # If we still don't have SQL, try to extract from answer
            if not clean_sql and answer:
                # The answer often contains the SQL - find the LAST SQLQuery occurrence
                all_sql_matches = list(re.finditer(r'SQLQuery:\s*([^\n]+(?:\n(?!SQLResult:|Answer:)[^\n]+)*)', answer, re.IGNORECASE))
                if all_sql_matches:
                    clean_sql = all_sql_matches[-1].group(1).strip()
                    # Remove any explanatory text after the SQL
                    if '\n' in clean_sql:
                        lines = clean_sql.split('\n')
                        sql_lines = []
                        for line in lines:
                            line_stripped = line.strip()
                            if line_stripped and not re.match(r'^(Question:|Please|Assuming|However|Note that)', line, re.IGNORECASE):
                                sql_lines.append(line)
                            elif sql_lines:  # Stop if we've already found SQL lines
                                break
                        clean_sql = '\n'.join(sql_lines).strip()
            
            # Try to extract result from verbose output if still no result
            if raw_result is None and answer:
                # Look for SQLResult: [...stuff...]
                result_match = re.search(r'SQLResult:\s*\[33;1m\[1;3m(.+?)\[0m', answer, re.DOTALL)
                if result_match:
                    result_str = result_match.group(1).strip()
                    # The result_str should be like [(1, 'data', ...), (2, ...)]
                    if result_str.startswith('[') and ']' in result_str:
                        # Extract just the list part
                        try:
                            import ast
                            raw_result = ast.literal_eval(result_str)
                            logger.info(f"Extracted result from verbose output: {len(raw_result) if isinstance(raw_result, list) else 'N/A'} rows")
                        except Exception as parse_err:
                            logger.warning(f"Failed to parse result from verbose output: {parse_err}")
            
            # Try to execute the SQL directly if we have it but no result
            if clean_sql and raw_result is None:
                try:
                    from sqlalchemy import text
                    
                    # Final cleanup: extract just the SELECT statement
                    if "SELECT" in clean_sql.upper():
                        # Find the last SELECT statement
                        select_match = re.search(r'(SELECT\s+.+?)(?:$|\n\n)', clean_sql, re.IGNORECASE | re.DOTALL)
                        if select_match:
                            clean_sql = select_match.group(1).strip()
                    
                    # Ensure user_id filter
                    if f"user_id" not in clean_sql.lower():
                        if "WHERE" in clean_sql.upper():
                            clean_sql = re.sub(
                                r"(WHERE)", rf"\1 user_id = {user_id} AND ", clean_sql, count=1, flags=re.IGNORECASE
                            )
                        else:
                            # Add WHERE clause before LIMIT, ORDER BY, or at the end
                            if "LIMIT" in clean_sql.upper():
                                clean_sql = re.sub(r"(\s+LIMIT\s+)", rf" WHERE user_id = {user_id}\1", clean_sql, flags=re.IGNORECASE)
                            elif "ORDER BY" in clean_sql.upper():
                                clean_sql = re.sub(r"(\s+ORDER\s+BY\s+)", rf" WHERE user_id = {user_id}\1", clean_sql, flags=re.IGNORECASE)
                            else:
                                clean_sql += f" WHERE user_id = {user_id}"
                    
                    # Execute the query
                    conn = db._engine.connect()
                    exec_result = conn.execute(text(clean_sql))
                    raw_result = exec_result.fetchall()
                    conn.close()
                    
                    # Convert Row objects to tuples for JSON serialization
                    if raw_result and len(raw_result) > 0:
                        raw_result = [tuple(row) for row in raw_result]
                    
                    logger.info(f"Direct execution got {len(raw_result) if raw_result else 0} rows")
                except Exception as exec_err:
                    logger.warning(f"Direct SQL execution failed: {exec_err}")

            # Parse result into proper format for frontend
            result_data = raw_result
            if raw_result and isinstance(raw_result, str):
                # If it's a string like "[(val1, val2), ...]", try to parse it
                try:
                    import ast
                    result_data = ast.literal_eval(raw_result)
                except:
                    result_data = raw_result
            
            return {
                "question": question,
                "sql": clean_sql,
                "result": result_data,
                "answer": answer,
            }

        except ValueError as ve:
            # API key not configured
            logger.error(f"Configuration error: {ve}")
            return {
                "question": question,
                "sql": "",
                "result": "",
                "answer": f"⚠️ Configuration Error: {str(ve)} The Text-to-SQL feature requires a valid Groq API key to generate SQL queries from natural language.",
            }
        except Exception as e:
            logger.error(f"Text-to-SQL error: {e}")
            return {
                "question": question,
                "sql": "",
                "result": "",
                "answer": f"Sorry, I couldn't process that query: {str(e)}",
            }


@lru_cache(maxsize=1)
def get_query_engine() -> TextToSQLEngine:
    return TextToSQLEngine()
