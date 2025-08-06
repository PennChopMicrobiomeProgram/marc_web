from typing import Optional
from typing_extensions import Annotated, TypedDict
from langchain import hub
from langgraph.graph import START, StateGraph
from langchain_openai import ChatOpenAI
from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import CreateTable

# Import SQLAlchemy models installed via requirements
from marc_db.models import Base


class QueryOutput(TypedDict):
    """Generated SQL query."""

    query: Annotated[str, ..., "Syntactically valid SQL query."]


class State(TypedDict):
    question: str
    query: str
    initial_query: Optional[str] = None


# Build schema from SQLAlchemy models
SCHEMA = "\n\n".join(
    str(CreateTable(table).compile(dialect=sqlite.dialect()))
    for table in Base.metadata.sorted_tables
)
GENERATE_QUERY_PROMPT = (
    lambda input: f"""
``` SYSTEM
Given an input question, create a syntactically correct SQLite3 query to run to help find the answer. Unless the user specifies in his question a specific number of examples they wish to obtain, you can return all the results that match the question.

Pay attention to use only the column names that you can see in the schema description. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.

Only use the following tables:
{SCHEMA}
```

``` USER
{input}
```
"""
)

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


def write_query(state: State) -> State:
    prompt = GENERATE_QUERY_PROMPT(state["question"])
    structured_llm = llm.with_structured_output(QueryOutput)
    result = structured_llm.invoke(prompt)
    return {"query": result["query"]}


def modify_query(state: State) -> State:
    prompt = query_prompt_template.invoke(
        {
            "dialect": "sqlite",
            "top_k": 10,
            "table_info": SCHEMA,
            "input": state["question"],
            "query": state["query"],
        }
    )
    structured_llm = llm.with_structured_output(QueryOutput)
    result = structured_llm.invoke(prompt)
    return {"query": result["query"]}


def generate_sql(question: str) -> str:
    graph_builder = StateGraph(State)
    graph_builder.add_node("write_query", write_query)
    graph_builder.add_edge(START, "write_query")
    graph = graph_builder.compile()
    result = graph.invoke({"question": question})
    return result["query"]


def generate_sql_modification(question: str, starting_query: str) -> str:
    graph_builder = StateGraph(State)
    graph_builder.add_node("modify_query", write_query)
    graph_builder.add_edge(START, "modify_query")
    graph = graph_builder.compile()
    result = graph.invoke({"question": question, "query": starting_query})
    return result["query"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate an SQL query for a natural language question."
    )
    parser.add_argument("question", help="User question to answer with SQL.")
    args = parser.parse_args()
    print(generate_sql(args.question))
