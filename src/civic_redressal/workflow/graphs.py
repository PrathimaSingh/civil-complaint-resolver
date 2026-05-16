from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from civic_redressal.agents.caption.agent import run_image_caption_agent, run_image_caption_bulk_agent
from civic_redressal.agents.ingestion.agent import run_ingestion_bulk_agent
from civic_redressal.workflow.state import ComplaintBatchState, ComplaintState
from civic_redressal.agents.intake.agent import run_intake_agent
from civic_redressal.agents.retrieval.agent import run_retrieval_agent, run_retrieval_llm_agent, run_retrieval_vision_llm_agent
from civic_redressal.agents.routing.agent import run_routing_agent
from civic_redressal.agents.registration.agent import run_registration_agent
from civic_redressal.agents.storage.agent import run_storage_agent, run_storage_bulk_agent
from civic_redressal.agents.analytics.agent import run_analytics_agent
from civic_redressal.agents.closure.agent import run_closure_agent

memory = MemorySaver()

workflow = StateGraph(ComplaintState)
workflow.add_node("intake", run_intake_agent)
workflow.add_node("router", run_routing_agent)
workflow.add_node("register", run_registration_agent)
workflow.add_node("storage", run_storage_agent)
workflow.add_node("tracker", run_analytics_agent)

workflow.add_edge(START, "intake")
workflow.add_edge("intake", "router")
workflow.add_edge("router", "register")
workflow.add_edge("register", "storage")
workflow.add_edge("storage", "tracker")
workflow.add_edge("tracker", END)

app = workflow.compile(checkpointer=memory)

rag_workflow = StateGraph(ComplaintState)
rag_workflow.add_node("retrieval", run_retrieval_agent)
rag_workflow.add_node("ragllm", run_retrieval_llm_agent)
rag_workflow.add_node("router", run_routing_agent)
rag_workflow.add_node("register", run_registration_agent)
rag_workflow.add_node("storage", run_storage_agent)
rag_workflow.add_node("tracker", run_analytics_agent)

rag_workflow.add_edge(START, "retrieval")
rag_workflow.add_edge("retrieval", "ragllm")
rag_workflow.add_edge("ragllm", "router")
rag_workflow.add_edge("router", "register")
rag_workflow.add_edge("register", "storage")
rag_workflow.add_edge("storage", "tracker")
rag_workflow.add_edge("tracker", END)

rag_app = rag_workflow.compile(checkpointer=memory)

rag_img_workflow = StateGraph(ComplaintState)
rag_img_workflow.add_node("caption", run_image_caption_agent)
rag_img_workflow.add_node("retrieval", run_retrieval_agent)
rag_img_workflow.add_node("ragllm", run_retrieval_vision_llm_agent)
rag_img_workflow.add_node("router", run_routing_agent)
rag_img_workflow.add_node("register", run_registration_agent)
rag_img_workflow.add_node("storage", run_storage_agent)
rag_img_workflow.add_node("tracker", run_analytics_agent)

rag_img_workflow.add_edge(START, "caption")
rag_img_workflow.add_edge("caption", "retrieval")
rag_img_workflow.add_edge("retrieval", "ragllm")
rag_img_workflow.add_edge("ragllm", "router")
rag_img_workflow.add_edge("router", "register")
rag_img_workflow.add_edge("register", "storage")
rag_img_workflow.add_edge("storage", "tracker")
rag_img_workflow.add_edge("tracker", END)

rag_img_app = rag_img_workflow.compile(checkpointer=memory)

#=========================Bulk Rag Ingestion (Text Only)- Complaint Analysis and Storage without Routing/Registration=========================
rag_ingest_workflow = StateGraph(ComplaintBatchState)
rag_ingest_workflow.add_node("ingestion", run_ingestion_bulk_agent)
rag_ingest_workflow.add_node("caption", run_image_caption_bulk_agent)
rag_ingest_workflow.add_node("storage", run_storage_bulk_agent)
rag_ingest_workflow.add_node("tracker", run_analytics_agent)

rag_ingest_workflow.add_edge(START, "ingestion")
rag_ingest_workflow.add_edge("ingestion", "caption")
rag_ingest_workflow.add_edge("caption", "storage")
rag_ingest_workflow.add_edge("storage", "tracker")
rag_ingest_workflow.add_edge("tracker", END)

rag_ingest_app = rag_ingest_workflow.compile(checkpointer=memory)

closeworkflow = StateGraph(ComplaintState)
closeworkflow.add_node("closer", run_closure_agent)
closeworkflow.add_edge(START, "closer")
closeworkflow.add_edge("closer", END)

close_app = closeworkflow.compile(checkpointer=memory)