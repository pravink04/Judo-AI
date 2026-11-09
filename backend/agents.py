import os
from dotenv import load_dotenv
from groq import Groq
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from backend.model import TicketState

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# --- 1. DYNAMIC MODEL SELECTOR (NO MORE 404 ERRORS) ---
try:
    client = Groq(api_key=api_key)
    models_data = client.models.list().data
    # Keep only text-based chat models (ignore guard/audio models)
    valid_chat_models = [m.id for m in models_data if "guard" not in m.id and "whisper" not in m.id]
    
    if not valid_chat_models:
        raise ValueError("No valid chat models found for this API key.")
        
    working_model = valid_chat_models[0] # Automatically pick the first allowed model
    print(f"\n✅ [SYSTEM] Successfully auto-selected model: {working_model}")
    
except Exception as e:
    print(f"\n❌ [SYSTEM] API Error: {str(e)}")
    working_model = "llama3-8b-8192" # Absolute fallback

# Initialize LangChain with the dynamically selected model
llm = ChatGroq(temperature=0.2, model_name=working_model)

# --- 2. KNOWLEDGE BASE (InMemory RAG) ---
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key="unga_gemini_key")
sample_policies = [
    Document(page_content="Hardware Policy: If a laptop screen is broken under warranty, we will replace it for free within 3-5 business days."),
    Document(page_content="Software Policy: For software login issues, clearing the browser cache or resetting the password solves 90% of cases."),
    Document(page_content="Billing Policy: Refunds for failed transactions take 7-10 working days to reflect in the original bank account."),
    Document(page_content="Accessories Policy: Defective peripherals such as a mouse, keyboard, headphones, or chargers are eligible for an immediate replacement within 6 months of purchase, provided the defective item is returned to the IT desk."),
    Document(page_content="Data Recovery Policy: The IT department does not offer data recovery services for physical or liquid-damaged devices. Employees must ensure all local files are synced to the company-provided Cloud Drive."),
    Document(page_content="Network & VPN Policy: Remote employees facing internal portal access issues must ensure they are connected to the official Company VPN. Reimbursements for home internet are strictly capped at $50 per month."),
    Document(page_content="Account Suspension Policy: User accounts inactive for more than 90 consecutive days are automatically suspended for security reasons. Reactivation requires direct email approval from the reporting manager."),
    Document(page_content="Premium Licensing Policy: Paid software licenses, such as Adobe Creative Cloud or AutoCAD, are not standard. They require a manager's approval ticket before the IT team can install them on a user's machine.")
]
vector_store = InMemoryVectorStore(embeddings)
vector_store.add_documents(sample_policies)
retriever = vector_store.as_retriever(search_kwargs={"k": 1})

# --- 3. AGENT WORKFLOW ---
def triage_agent(state: TicketState):
    print("\n🔍 [Agent: Triage] Categorizing ticket...")
    prompt = PromptTemplate.from_template(
        "Analyze this customer ticket and categorize it into ONE of these: "
        "[Hardware, Software, Billing, Other].\nTicket: {ticket}\nCategory:"
    )
    chain = prompt | llm
    result = chain.invoke({"ticket": state["message"]})
    return {"category": result.content.strip()}

def retrieval_agent(state: TicketState):
    print("📚 [Agent: Retrieval] Fetching policy context...")
    docs = retriever.invoke(state["message"])
    fetched_context = "\n".join([doc.page_content for doc in docs])
    return {"context": fetched_context}

def resolution_agent(state: TicketState):
    print("🧠 [Agent: Resolution] Drafting final response...")
    prompt = PromptTemplate.from_template(
        "You are Nexus AI Support.\n"
        "Customer Issue: {ticket}\n"
        "Category: {category}\n"
        "Company Policy: {context}\n\n"
        "Based ONLY on the Company Policy provided above, write a polite, "
        "professional, and helpful response solving the customer's exact issue.\nResponse:"
    )
    chain = prompt | llm
    result = chain.invoke({
        "ticket": state["message"],
        "category": state["category"],
        "context": state["context"] 
    })
    return {"response": result.content.strip()}