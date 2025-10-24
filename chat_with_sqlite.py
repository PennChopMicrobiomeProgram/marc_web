# DEMO NLQ

# Simplest form, single shot, single prompt
# Replace with CHOP model and API key once available
# llm = OllamaLLM(model="llama3.2:latest")
# db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)
# db_chain.invoke("How many isolates are in the database?")
# db_chain.invoke("Can you tell me the names of the isolates with 0 aliquots?")


from IPython.display import Image, display
from langchain.chat_models import init_chat_model
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.sql import SQLDatabaseChain
from langchain_ollama.llms import OllamaLLM
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import create_react_agent
from typing_extensions import Annotated, TypedDict


class QueryOutput(TypedDict):
    """Generated SQL query."""

    query: Annotated[str, ..., "Syntactically valid SQL query."]


class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str


db = SQLDatabase.from_uri("sqlite:////home/ctbus/Penn/marc_web/db.sqlite")
llm = init_chat_model("mistral-small", model_provider="ollama")

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

QUERY_SYSTEM_PROMPT = """
You are an expert SQL query builder for {dialect} databases.

Use the following database schema:
{table_info}

Return a syntactically valid SQL statement that answers the user's question.
Unless the user specifies a row limit, default to returning up to {top_k} results.
If an existing query is provided, treat it as a starting point and refine it if appropriate.

Existing query draft (may be empty):
{existing_query}
"""

query_prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", QUERY_SYSTEM_PROMPT),
        ("human", "{input}"),
    ]
)


def write_query(state: State) -> State:
    """Generate SQL query to fetch information."""
    prompt = query_prompt_template.invoke(
        {
            "dialect": "sqlite",
            "top_k": 10,
            "table_info": db.get_table_info(),
            "existing_query": state.get("query", ""),
            "input": state["question"],
        }
    )
    structured_llm = llm.with_structured_output(QueryOutput)
    result = structured_llm.invoke(prompt)
    return {"query": result["query"]}


def execute_query(state: State):
    """Execute SQL query."""
    execute_query_tool = QuerySQLDatabaseTool(db=db)
    return {"result": execute_query_tool.invoke(state["query"])}


def generate_answer(state: State):
    """Answer question using retrieved information as context."""
    prompt = (
        "Given the following user question, corresponding SQL query, "
        "and SQL result, answer the user question.\n\n"
        f'Question: {state["question"]}\n'
        f'SQL Query: {state["query"]}\n'
        f'SQL Result: {state["result"]}'
    )
    response = llm.invoke(prompt)
    return {"answer": response.content}


if True:
    graph_builder = StateGraph(State).add_sequence(
        [write_query, execute_query, generate_answer]
    )
    graph_builder.add_edge(START, "write_query")
    graph = graph_builder.compile()
    # display(Image(graph.get_graph().draw_mermaid_png()))

    for step in graph.stream(
        {"question": "What is the average number of aliquots per isolate?"},
        stream_mode="updates",
    ):
        print(step)
else:
    system_message = query_prompt_template.format(dialect="SQLite", top_k=5)

    agent_executor = create_react_agent(llm, tools, prompt=system_message)

    question = "What is the average number of aliquots per isolate?"

    for step in agent_executor.stream(
        {"messages": [{"role": "user", "content": question}]},
        stream_mode="values",
    ):
        step["messages"][-1].pretty_print()
