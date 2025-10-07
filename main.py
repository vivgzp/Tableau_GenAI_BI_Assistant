import os
import logging
import sys # Added for graceful exit on missing env vars
from dotenv import load_dotenv

# Import LangSmith tracing (debugging in LangSmith.com)
from langsmith import Client

# Langgraph and LangChain packages
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_tableau.tools.simple_datasource_qa import initialize_simple_datasource_qa
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# --- MOCK UTILITIES (Since external utilities.chat and utilities.prompt are not provided) ---

# Mock Print Stream for streaming output
def print_stream(stream):
    """Prints the content of the LangGraph stream and returns the final response string."""
    final_output_content = ""
    for chunk in stream:
        # LangGraph typically yields dictionaries where the last message holds the content
        if "messages" in chunk and chunk["messages"]:
            latest_message = chunk["messages"][-1]
            if isinstance(latest_message, AIMessage):
                content = latest_message.content
                print(content, end="", flush=True)
                final_output_content += content
    print() # Ensure a final newline
    return final_output_content

# Mock System Prompt for the agent
AGENT_SYSTEM_PROMPT = """
You are a helpful and highly skilled data analysis agent. 
Your goal is to answer questions about Tableau data using the provided tool: 'analyze_datasource'.
Maintain a concise and conversational tone and use the chat history to inform your answers.

IMPORTANT CONSTRAINT: If a user asks for 'Top N' results, you must return the full dataset 
and advise the user to filter the results on their side, as the Tableau tool cannot apply 
the 'limit' property.
"""
# -----------------------------------------------------------------------------------------


# Load environment
load_dotenv()

# Add LangSmith tracing
langsmith_client = Client()

config = {
    "run_name": "Tableau Langchain Chat Agent"
}

def create_agent():
    """Initializes the Tableau tool and the LangGraph agent."""
    
    # Check for required environment variables
    required_vars = ['TABLEAU_DOMAIN', 'TABLEAU_SITE', 'TABLEAU_JWT_CLIENT_ID', 
                     'TABLEAU_JWT_SECRET_ID', 'TABLEAU_JWT_SECRET', 'TABLEAU_USER', 
                     'TABLEAU_API_VERSION', 'DATASOURCE_LUID', 'OPENAI_API_KEY']
    
    for var in required_vars:
        if not os.getenv(var):
            print(f"ERROR: Missing required environment variable: {var}. Please check your .env file.", file=sys.stderr)
            return None, None

    # Define the model name before initialization (Fixes the AttributeError)
    tool_model_name = "gpt-4o-mini"
    
    # Initialize the Tableau data source tool
    analyze_datasource = initialize_simple_datasource_qa(
        domain=os.environ['TABLEAU_DOMAIN'],
        site=os.environ['TABLEAU_SITE'],
        jwt_client_id=os.environ['TABLEAU_JWT_CLIENT_ID'],
        jwt_secret_id=os.environ['TABLEAU_JWT_SECRET_ID'],
        jwt_secret=os.environ['TABLEAU_JWT_SECRET'],
        tableau_api_version=os.environ['TABLEAU_API_VERSION'],
        tableau_user=os.environ['TABLEAU_USER'],
        datasource_luid=os.environ['DATASOURCE_LUID'],
        # Using a valid, low-cost OpenAI model for tool query generation
        tooling_llm_model=tool_model_name, 
        model_provider="openai"
    )
    
    # Use the local variable instead of accessing a non-existent attribute
    print(f"INFO: Tableau Tool initialized using {tool_model_name} for query generation.")

    # Create the agent LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) # Switched to a conversational model
    tools = [analyze_datasource]

    # Create the LangGraph agent (ReAct style)
    agent = create_react_agent(
        model=llm, 
        tools=tools,
        prompt=AGENT_SYSTEM_PROMPT
    )
    return agent

# --- Execution ---

if __name__ == "__main__":
    TableauLangChain = create_agent()

    if TableauLangChain is None:
        sys.exit(1)

    # List to store the history of messages (HumanMessage and AIMessage objects)
    chat_history: list[BaseMessage] = []

    print("\n" + "="*50)
    print(" Tableau Conversational Data Agent ")
    print("="*50)
    print("Start chatting! Type 'quit' or 'exit' to end the session.")
    print("----------------------------------------------------------")

    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ["quit", "exit"]:
            print("Session ended. bye!")
            break

        if not user_input.strip():
            continue

        # 1. Add current user message to history
        chat_history.append(HumanMessage(content=user_input))

        # 2. Construct the input dictionary for LangGraph/LangChain
        # LangGraph agents require the entire history to be passed in the 'messages' key.
        messages_input = {"messages": chat_history}
        
        # 3. Run the agent stream
        print("Agent: ", end="", flush=True)
        
        try:
            stream = TableauLangChain.stream(messages_input, config=config, stream_mode="values")
            agent_response_content = print_stream(stream)
            
            # 4. Add the full agent response to history for the next turn
            if agent_response_content:
                chat_history.append(AIMessage(content=agent_response_content))
                
        except Exception as e:
            print(f"\n[ERROR] Agent execution failed: {e}", file=sys.stderr)
            # Remove the last user message to allow retry without polluting history
            chat_history.pop() 
