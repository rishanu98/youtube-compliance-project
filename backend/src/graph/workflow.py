from langgraph.graph import StateGraph, MessagesState, START, END
from .state import VideoAuditState
from backend.src.graph.nodes import index_video, compliance_check

def create_workflow():
    graph = StateGraph(VideoAuditState) # intialize the graph with the state schema

    # Define the states and their corresponding nodes
    graph.add_node("index_video", index_video)
    graph.add_node("compliance_check", compliance_check)

    # Define the transitions between states
    graph.set_entry_point("index_video")
    graph.add_edge("index_video", "compliance_check")
    graph.add_edge("compliance_check", END)

    app = graph.compile()

    return app

app = create_workflow()
