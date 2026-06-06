// ==========================================
// LearnGraph AI - Neo4j Seed Graph
// File: seed_graph.cypher
// ==========================================
// This script creates the 19 core concepts and their prerequisite relationships.
// It uses MERGE to ensure idempotency (safe to run multiple times).

// 1. Constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Student) REQUIRE s.id IS UNIQUE;

// 2. Create Concepts
MERGE (c1:Concept {id: 'arrays', name: 'Arrays', difficulty: 1, bloom_target: 4})
MERGE (c2:Concept {id: 'strings', name: 'Strings', difficulty: 1, bloom_target: 4})
MERGE (c3:Concept {id: 'linked_lists', name: 'Linked Lists', difficulty: 2, bloom_target: 4})
MERGE (c4:Concept {id: 'stacks', name: 'Stacks', difficulty: 2, bloom_target: 4})
MERGE (c5:Concept {id: 'queues', name: 'Queues', difficulty: 2, bloom_target: 4})
MERGE (c6:Concept {id: 'recursion', name: 'Recursion', difficulty: 3, bloom_target: 4})
MERGE (c7:Concept {id: 'trees', name: 'Trees', difficulty: 3, bloom_target: 4})
MERGE (c8:Concept {id: 'bst', name: 'BST', difficulty: 3, bloom_target: 4})
MERGE (c9:Concept {id: 'heap', name: 'Heap', difficulty: 4, bloom_target: 4})
MERGE (c10:Concept {id: 'dfs', name: 'DFS', difficulty: 4, bloom_target: 4})
MERGE (c11:Concept {id: 'bfs', name: 'BFS', difficulty: 4, bloom_target: 4})
MERGE (c12:Concept {id: 'graphs', name: 'Graphs', difficulty: 4, bloom_target: 4})
MERGE (c13:Concept {id: 'hash_tables', name: 'Hash Tables', difficulty: 2, bloom_target: 4})
MERGE (c14:Concept {id: 'binary_search', name: 'Binary Search', difficulty: 2, bloom_target: 4})
MERGE (c15:Concept {id: 'greedy', name: 'Greedy', difficulty: 4, bloom_target: 4})
MERGE (c16:Concept {id: 'dynamic_programming', name: 'Dynamic Programming', difficulty: 5, bloom_target: 4})
MERGE (c17:Concept {id: 'two_pointers', name: 'Two Pointers', difficulty: 2, bloom_target: 4})
MERGE (c18:Concept {id: 'sliding_window', name: 'Sliding Window', difficulty: 3, bloom_target: 4})
MERGE (c19:Concept {id: 'prefix_sum', name: 'Prefix Sum', difficulty: 2, bloom_target: 4});

// 3. Create PREREQUISITE_OF Edges
// Level 1 (Arrays) -> Level 2
MATCH (arrays:Concept {id: 'arrays'}), (strings:Concept {id: 'strings'})
MERGE (arrays)-[:PREREQUISITE_OF {strength: 1.0}]->(strings);

MATCH (arrays:Concept {id: 'arrays'}), (hash_tables:Concept {id: 'hash_tables'})
MERGE (arrays)-[:PREREQUISITE_OF {strength: 0.8}]->(hash_tables);

MATCH (arrays:Concept {id: 'arrays'}), (binary_search:Concept {id: 'binary_search'})
MERGE (arrays)-[:PREREQUISITE_OF {strength: 1.0}]->(binary_search);

MATCH (arrays:Concept {id: 'arrays'}), (linked_lists:Concept {id: 'linked_lists'})
MERGE (arrays)-[:PREREQUISITE_OF {strength: 0.5}]->(linked_lists);

MATCH (arrays:Concept {id: 'arrays'}), (two_pointers:Concept {id: 'two_pointers'})
MERGE (arrays)-[:PREREQUISITE_OF {strength: 1.0}]->(two_pointers);

MATCH (arrays:Concept {id: 'arrays'}), (prefix_sum:Concept {id: 'prefix_sum'})
MERGE (arrays)-[:PREREQUISITE_OF {strength: 1.0}]->(prefix_sum);

// Two Pointers -> Sliding Window
MATCH (two_pointers:Concept {id: 'two_pointers'}), (sliding_window:Concept {id: 'sliding_window'})
MERGE (two_pointers)-[:PREREQUISITE_OF {strength: 1.0}]->(sliding_window);

// Prefix Sum -> Sliding Window
MATCH (prefix_sum:Concept {id: 'prefix_sum'}), (sliding_window:Concept {id: 'sliding_window'})
MERGE (prefix_sum)-[:PREREQUISITE_OF {strength: 1.0}]->(sliding_window);

// Level 2 (Linked Lists, Hash Tables) -> Stacks, Queues
MATCH (arrays:Concept {id: 'arrays'}), (stacks:Concept {id: 'stacks'})
MERGE (arrays)-[:PREREQUISITE_OF {strength: 0.5}]->(stacks);

MATCH (linked_lists:Concept {id: 'linked_lists'}), (stacks:Concept {id: 'stacks'})
MERGE (linked_lists)-[:PREREQUISITE_OF {strength: 0.8}]->(stacks);

MATCH (arrays:Concept {id: 'arrays'}), (queues:Concept {id: 'queues'})
MERGE (arrays)-[:PREREQUISITE_OF {strength: 0.5}]->(queues);

MATCH (linked_lists:Concept {id: 'linked_lists'}), (queues:Concept {id: 'queues'})
MERGE (linked_lists)-[:PREREQUISITE_OF {strength: 0.8}]->(queues);

// Recursion -> Trees, DFS, DP
MATCH (recursion:Concept {id: 'recursion'}), (trees:Concept {id: 'trees'})
MERGE (recursion)-[:PREREQUISITE_OF {strength: 1.0}]->(trees);

MATCH (recursion:Concept {id: 'recursion'}), (dfs:Concept {id: 'dfs'})
MERGE (recursion)-[:PREREQUISITE_OF {strength: 1.0}]->(dfs);

MATCH (recursion:Concept {id: 'recursion'}), (dynamic_programming:Concept {id: 'dynamic_programming'})
MERGE (recursion)-[:PREREQUISITE_OF {strength: 1.0}]->(dynamic_programming);

// Stacks/Queues -> DFS/BFS
MATCH (stacks:Concept {id: 'stacks'}), (dfs:Concept {id: 'dfs'})
MERGE (stacks)-[:PREREQUISITE_OF {strength: 1.0}]->(dfs);

MATCH (queues:Concept {id: 'queues'}), (bfs:Concept {id: 'bfs'})
MERGE (queues)-[:PREREQUISITE_OF {strength: 1.0}]->(bfs);

// Trees -> BST, Heap, Graphs, DFS, BFS
MATCH (trees:Concept {id: 'trees'}), (bst:Concept {id: 'bst'})
MERGE (trees)-[:PREREQUISITE_OF {strength: 1.0}]->(bst);

MATCH (trees:Concept {id: 'trees'}), (heap:Concept {id: 'heap'})
MERGE (trees)-[:PREREQUISITE_OF {strength: 0.8}]->(heap);

MATCH (trees:Concept {id: 'trees'}), (graphs:Concept {id: 'graphs'})
MERGE (trees)-[:PREREQUISITE_OF {strength: 0.5}]->(graphs);

MATCH (trees:Concept {id: 'trees'}), (dfs:Concept {id: 'dfs'})
MERGE (trees)-[:PREREQUISITE_OF {strength: 1.0}]->(dfs);

MATCH (trees:Concept {id: 'trees'}), (bfs:Concept {id: 'bfs'})
MERGE (trees)-[:PREREQUISITE_OF {strength: 1.0}]->(bfs);

// Graphs -> DFS, BFS
MATCH (graphs:Concept {id: 'graphs'}), (dfs:Concept {id: 'dfs'})
MERGE (graphs)-[:PREREQUISITE_OF {strength: 1.0}]->(dfs);

MATCH (graphs:Concept {id: 'graphs'}), (bfs:Concept {id: 'bfs'})
MERGE (graphs)-[:PREREQUISITE_OF {strength: 1.0}]->(bfs);
