# DEMO NLQ

from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain_ollama.llms import OllamaLLM


db = SQLDatabase.from_uri("sqlite:////home/ctbus/Penn/marc_web/db.sqlite")
# Replace with CHOP model and API key once available
llm = OllamaLLM(model="llama3.2:latest")
db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)

db_chain.invoke("How many isolates are in the database?")

db_chain.invoke("Can you tell me the names of the isolates with 0 aliquots?")
