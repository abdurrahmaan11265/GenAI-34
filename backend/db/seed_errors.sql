-- LearnGraph AI - Error Taxonomy Seed Data
-- This file populates the error_taxonomy table used by the Misconception Detector.

INSERT INTO error_taxonomy (id, name, description, concept) VALUES
    (gen_random_uuid(), 'base_case_confusion', 'Base Case Confusion', 'Failure to identify or correctly implement the base case, leading to infinite recursion or incorrect early returns.', 'recursion'),
    (gen_random_uuid(), 'stack_frame_confusion', 'Stack Frame Confusion', 'Misunderstanding how recursive calls are pushed onto the call stack and how state is preserved/restored upon return.', 'recursion'),
    (gen_random_uuid(), 'infinite_recursion', 'Infinite Recursion', 'A recursive call that does not progress towards a base case.', 'recursion'),
    
    (gen_random_uuid(), 'dfs_bfs_confusion', 'DFS/BFS Confusion', 'Using a depth-first approach when a breadth-first approach is optimal, or vice versa, often mixing stack and queue logic.', 'trees'),
    (gen_random_uuid(), 'leaf_node_confusion', 'Leaf Node Confusion', 'Failing to handle leaf nodes correctly (e.g., assuming a node with one child is a leaf).', 'trees'),
    
    (gen_random_uuid(), 'directed_undirected_confusion', 'Directed vs Undirected Confusion', 'Treating a directed graph as undirected or failing to prevent reverse traversal in an undirected graph.', 'graphs'),
    (gen_random_uuid(), 'traversal_cycle', 'Traversal Cycle', 'Failing to track visited nodes, leading to infinite loops during graph traversal.', 'graphs'),
    
    (gen_random_uuid(), 'off_by_one', 'Off-by-One Error', 'Loop bounds or array indices are off by exactly one (e.g., <= instead of <).', 'arrays'),
    (gen_random_uuid(), 'index_out_of_bounds', 'Index Out of Bounds', 'Attempting to access an array or list element outside its allocated memory/bounds.', 'arrays')
ON CONFLICT DO NOTHING;
