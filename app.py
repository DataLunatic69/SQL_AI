import streamlit as st
from langchain.agents import initialize_agent
from langchain_community.utilities import SQLDatabase  
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StdOutCallbackHandler
from langchain.tools import Tool
from langchain_core.output_parsers import JsonOutputParser
from sqlalchemy import create_engine
from config import config
from urllib.parse import quote  
from langchain_groq import ChatGroq
import os

st.set_page_config(page_title="LangChain: Postgres AI", page_icon="📚")
st.title("📚 LangChain: Postgres AI")


api_key = st.sidebar.text_input(label="Groq API Key", type="password")
if not api_key:
    st.error("Groq API Key not found. Please enter it in the sidebar.")
    st.stop()


llm = ChatGroq(groq_api_key=api_key, model_name="qwen/qwen3-32b", streaming=True)



def configure_db():
    """Establish and return a connection to the PostgreSQL database using SQLAlchemy."""
    try:
        
        params = config()

        
        user = quote(params["user"])
        password = quote(params["password"])
        host = params["host"]
        port = params["port"]
        database = params["database"]

        
        connection_string = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
        print(f"Connection string: {connection_string}")  

        
        engine = create_engine(connection_string)
        return SQLDatabase(engine)
    except KeyError as key_error:
        st.error(f"Missing database connection parameter: {key_error}")
        st.stop()
    except Exception as e:
        st.error(f"Failed to configure the database: {e}")
        st.stop()






try:
    db = configure_db()
except Exception as e:
    st.error(f"Database configuration failed: {e}")
    st.stop()


def query_database(query):
    try:
        print(f"Executing query: {query}")  
        sanitized_query = query.strip().strip(";")
        return db.run(sanitized_query)
    except Exception as e:
        st.error(f"Query execution failed: {e}")
        
        return None



output_parser = JsonOutputParser()

description = """
Use this to query the deal database tables.
Available tables:
- customers: customer_id, registration_date, city, gender
- orders: order_id, customer_id, order_date, total_amount, status  
- order_items: item_id, order_id, product_name, quantity, unit_price
"""



agent = initialize_agent(
    tools=[Tool(name="SQL Query Tool", func=query_database, description=description)],
    llm=llm,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    output_parser=output_parser,
    handle_parsing_errors=True  
)


if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]


for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])


user_query = st.chat_input(placeholder="Ask anything from the database")

few_shot_examples = """

"""


few_shot_prompt = f"{few_shot_examples}\nUser Query: {user_query}"

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        stdout_callback = StdOutCallbackHandler()
        try:
            response = agent.run(user_query, callbacks=[stdout_callback])
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.write(response)
        except Exception as e:
            st.error(f"Failed to process the query: {e}")