// ==========================================
// LearnGraph AI - Neo4j Core Queries
// File: core_queries.cypher
// ==========================================

// 1. Attach Student (Initialize Student Node)
// Run when a user registers or starts their first session
MERGE (s:Student {id: $student_id});

// 2. Set Currently Learning (Session Start)
// Run when the student begins a new learning session
MATCH (s:Student {id: $student_id})
MATCH (c:Concept {id: $concept_id})
OPTIONAL MATCH (s)-[old:CURRENTLY_LEARNING]->()
DELETE old
MERGE (s)-[:CURRENTLY_LEARNING {started_at: datetime()}]->(c);

// 3. Update Mastery (Create or Update HAS_MASTERY edge)
// Run by the Progress Agent after a quiz attempt
MATCH (s:Student {id: $student_id})
MATCH (c:Concept {id: $concept_id})
MERGE (s)-[m:HAS_MASTERY]->(c)
SET m.score = $mastery_score,
    m.bloom_level = $bloom_level,
    m.updated_at = datetime()
WITH s, c
// Remove CURRENTLY_LEARNING if they mastered it (only for this concept)
OPTIONAL MATCH (s)-[cl:CURRENTLY_LEARNING]->(c)
DELETE cl;

// 4. Mark Struggles With (Error Tracking)
// Run by the Progress Agent if a student makes a specific error
MATCH (s:Student {id: $student_id})
MATCH (c:Concept {id: $concept_id})
MERGE (s)-[e:STRUGGLES_WITH {error_type: $error_type}]->(c)
ON CREATE SET e.count = 1, e.last_seen_at = datetime()
ON MATCH SET e.count = e.count + 1, e.last_seen_at = datetime();

// 5. Get Eligible Concepts (Frontier of Knowledge)
// Returns concepts where ALL prerequisites have mastery >= 0.85
// AND the concept itself has mastery < 0.85 (or no mastery edge)
MATCH (c:Concept)
WHERE NOT EXISTS {
    MATCH (s:Student {id: $student_id})-[m:HAS_MASTERY]->(c)
    WHERE m.score >= 0.85
}
AND NOT EXISTS {
    MATCH (pre:Concept)-[:PREREQUISITE_OF]->(c)
    WHERE NOT EXISTS {
        MATCH (s:Student {id: $student_id})-[m:HAS_MASTERY]->(pre)
        WHERE m.score >= 0.85
    }
}
RETURN c.id AS concept_id, c.name AS name, c.difficulty AS difficulty;

// 6. Get Newly Unlocked Concepts
// Specifically fetches concepts that the user has NEVER encountered before
// but whose prerequisites are now fully satisfied (often run right after a mastery update)
MATCH (c:Concept)
WHERE NOT EXISTS {
    MATCH (s:Student {id: $student_id})-[m:HAS_MASTERY]->(c)
}
AND NOT EXISTS {
    MATCH (pre:Concept)-[:PREREQUISITE_OF]->(c)
    WHERE NOT EXISTS {
        MATCH (s:Student {id: $student_id})-[m:HAS_MASTERY]->(pre)
        WHERE m.score >= 0.85
    }
}
RETURN c.id AS concept_id, c.name AS name;

// 7. Get Recommended Concept (Lowest Dependency Depth for a Target)
// If the student wants to learn a target (e.g., "dynamic_programming"),
// this finds ALL unmet prerequisites and returns the one closest to the roots.
MATCH path = (req:Concept)-[:PREREQUISITE_OF*]->(target:Concept {id: $target_concept_id})
WHERE NOT EXISTS {
    MATCH (s:Student {id: $student_id})-[m:HAS_MASTERY]->(req)
    WHERE m.score >= 0.85
}
// Ensure the recommended concept actually has its own prerequisites met
AND NOT EXISTS {
    MATCH (pre:Concept)-[:PREREQUISITE_OF]->(req)
    WHERE NOT EXISTS {
        MATCH (s:Student {id: $student_id})-[m2:HAS_MASTERY]->(pre)
        WHERE m2.score >= 0.85
    }
}
// Return the one with the lowest path depth towards the target
RETURN req.id AS recommended_concept_id, length(path) AS dependency_depth
ORDER BY dependency_depth DESC
LIMIT 1;

// 8. Replan Curriculum (Holistic State Query)
// Returns weak concepts that need review AND eligible concepts to learn next
// Used by the Curriculum Agent to generate the next path
CALL {
    MATCH (s:Student {id: $student_id})-[m:HAS_MASTERY]->(c:Concept)
    WHERE m.score < 0.85 AND m.score > 0.0
    RETURN c.id AS concept_id, 'review' AS action, m.score AS current_score, c.difficulty AS difficulty
    
    UNION
    
    MATCH (c:Concept)
    WHERE NOT EXISTS {
        MATCH (s:Student {id: $student_id})-[m:HAS_MASTERY]->(c)
        WHERE m.score >= 0.85
    }
    AND NOT EXISTS {
        MATCH (pre:Concept)-[:PREREQUISITE_OF]->(c)
        WHERE NOT EXISTS {
            MATCH (s:Student {id: $student_id})-[m:HAS_MASTERY]->(pre)
            WHERE m.score >= 0.85
        }
    }
    RETURN c.id AS concept_id, 'learn' AS action, 0.0 AS current_score, c.difficulty AS difficulty
}
RETURN concept_id, action, current_score, difficulty
ORDER BY action DESC, difficulty ASC;

// 9. Get Student Learning State (Graph Snapshot for Agent)
// Gives the agent context on the student's mastery of the local neighborhood
MATCH (s:Student {id: $student_id})-[m:HAS_MASTERY]->(c:Concept)
OPTIONAL MATCH (s)-[e:STRUGGLES_WITH]->(c)
OPTIONAL MATCH (s)-[cl:CURRENTLY_LEARNING]->(c)
RETURN 
    c.id AS concept_id, 
    m.score AS mastery_score, 
    m.bloom_level AS bloom_level, 
    collect(e.error_type) AS errors,
    (cl IS NOT NULL) AS is_currently_learning;

// 10. Graph Visualization Query - Nodes (D3.js Frontend)
// Returns all concepts with student mastery appended
MATCH (c:Concept)
OPTIONAL MATCH (s:Student {id: $student_id})-[m:HAS_MASTERY]->(c)
OPTIONAL MATCH (s)-[cl:CURRENTLY_LEARNING]->(c)
RETURN 
    c.id AS id, 
    c.name AS name,
    c.difficulty AS difficulty,
    COALESCE(m.score, 0.0) AS mastery_score,
    (cl IS NOT NULL) AS is_currently_learning;

// 11. Graph Visualization Query - Edges (D3.js Frontend)
// Returns pure topology for D3 links
MATCH (source:Concept)-[r:PREREQUISITE_OF]->(target:Concept)
RETURN 
    source.id AS source, 
    target.id AS target, 
    r.strength AS value;

// 12. Get Current Learning Focus
// Fetches the concept the student is actively studying in their current session.
MATCH (s:Student {id: $student_id})-[:CURRENTLY_LEARNING]->(c:Concept)
RETURN 
    c.id AS concept_id, 
    c.name AS name, 
    c.difficulty AS difficulty;
