import networkx as nx
import matplotlib.pyplot as plt

class MemoryGraph:
    def __init__(self):
        self.graph = nx.Graph()

    def add(self, percept):
        self.graph.add_node(percept.id, text=percept.text, tags=percept.tags, emotion=percept.emotion, time=percept.timestamp)
        self._link(percept)

    def _link(self, new_percept):
        nodes = list(self.graph.nodes(data=True))[-5:]
        for pid, data in nodes:
            if data['emotion'] == new_percept.emotion or any(tag in data['tags'] for tag in new_percept.tags):
                self.graph.add_edge(new_percept.id, pid, reason="emotion/tag match")

    def show(self):
        labels = {node: data['text'][:20] + '...' for node, data in self.graph.nodes(data=True)}
        pos = nx.spring_layout(self.graph)
        nx.draw(self.graph, pos, with_labels=True, labels=labels, node_size=1000, node_color='skyblue', font_size=8)
        plt.title("🧠 Cognix+ Memory Graph")
        plt.show()
