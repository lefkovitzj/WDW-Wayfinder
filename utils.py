"""
Project Name: WDW-Transit-Optimizer
File Name: utils.py
Description: Utility functions for pathfinding algorithms.
Author: Joseph Lefkovitz (github.com/lefkovitzj)
Last Modified: 1/8/2026
"""
import heapq

def djikstra(graph, start):
    """
    Mode-Aware Dijkstra's algorithm to find the shortest paths from start to all other nodes.
    Expects graph format: { node: { neighbor: { 'weight': int, 'mode': str } } }
    """
    queue = [(0, start)]
    min_cost = {start: 0}
    # Stores (parent, mode)
    best_path = {start: (None, None)}

    while queue:
        current_cost, current_node = heapq.heappop(queue)

        if current_cost > min_cost.get(current_node, float('inf')):
            continue

        for neighbor, edge_data in graph.get(current_node, {}).items():
            # weight and mode are extracted from the edge metadata
            weight = edge_data['weight']
            mode = edge_data['mode']

            new_cost = current_cost + weight

            if new_cost < min_cost.get(neighbor, float('inf')):
                min_cost[neighbor] = new_cost
                best_path[neighbor] = (current_node, mode)
                heapq.heappush(queue, (new_cost, neighbor))

    return min_cost, best_path
