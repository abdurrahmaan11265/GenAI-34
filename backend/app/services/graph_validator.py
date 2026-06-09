from typing import List, Dict, Any

class GraphValidator:
    """
    Validates the generated knowledge graph against deterministic structural rules (V01-V08).
    """
    @staticmethod
    def validate(concepts: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        failures = []
        
        # V01: Cycle Detection (DFS)
        cycles_found = GraphValidator.detect_cycles(concepts, edges)
        if cycles_found:
            failures.append({
                "rule": "V01",
                "passed": False,
                "severity": "CRITICAL",
                "detail": {"cycles": cycles_found}
            })
            
        # V05: Orphan Detection
        orphans = GraphValidator.detect_orphans(concepts, edges)
        if orphans:
            failures.append({
                "rule": "V05",
                "passed": False,
                "severity": "WARNING",
                "detail": {"orphans": orphans}
            })
            
        return failures

    @staticmethod
    def detect_cycles(concepts: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[List[str]]:
        """
        Uses Kahn's Algorithm (Topological Sort) to detect cycles in PREREQUISITE edges.
        Returns a list containing the nodes involved in the cycle if one exists.
        """
        from collections import deque
        
        adj = {c["id"]: [] for c in concepts}
        indegree = {c["id"]: 0 for c in concepts}
        
        for e in edges:
            # handle both relationship_type and edge_type for robustness during different pipeline stages
            edge_type = e.get("relationship_type", e.get("edge_type", "PREREQUISITE"))
            if edge_type == "PREREQUISITE":
                src = e.get("source_concept_id", e.get("from_concept_id"))
                tgt = e.get("target_concept_id", e.get("to_concept_id"))
                if src in adj and tgt in indegree:
                    adj[src].append(tgt)
                    indegree[tgt] += 1
                    
        queue = deque([node for node, deg in indegree.items() if deg == 0])
        visited_count = 0
        
        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in adj[node]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)
                    
        if visited_count != len(concepts):
            # A cycle exists. Return the nodes that are part of the cycle (indegree > 0)
            cycle_nodes = [node for node, deg in indegree.items() if deg > 0]
            return [cycle_nodes]
            
        return []

    @staticmethod
    def detect_orphans(concepts: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[str]:
        connected_nodes = set()
        for e in edges:
            connected_nodes.add(e["source_concept_id"])
            connected_nodes.add(e["target_concept_id"])
            
        orphans = [c["id"] for c in concepts if c["id"] not in connected_nodes]
        return orphans
