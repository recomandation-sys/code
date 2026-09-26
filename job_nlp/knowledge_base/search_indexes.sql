CREATE VIRTUAL TABLE occupation_search USING fts5(occupation_id UNINDEXED, title, aliases, description, tokenize='unicode61');
INSERT INTO occupation_search SELECT o.occupation_id,o.preferred_label,COALESCE(group_concat(a.label,' | '),''),o.description FROM occupation o LEFT JOIN occupation_alias a USING(occupation_id) WHERE o.scope IN ('core','conditional') GROUP BY o.occupation_id;
CREATE VIRTUAL TABLE task_search USING fts5(task_id UNINDEXED, description, tokenize='unicode61');
INSERT INTO task_search SELECT task_id,description FROM task;
CREATE VIRTUAL TABLE skill_search USING fts5(skill_id UNINDEXED,label,aliases,description,tokenize='unicode61');
INSERT INTO skill_search SELECT s.skill_id,s.preferred_label,COALESCE(group_concat(a.label,' | '),''),s.description FROM skill s LEFT JOIN skill_alias a USING(skill_id) GROUP BY s.skill_id;
