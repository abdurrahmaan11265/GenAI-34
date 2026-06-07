import ast
import re
import glob

gen_file = 'backend/generated_models.py'
with open(gen_file, 'r', encoding='utf-8-sig') as f:
    gen_code = f.read()

gen_module = ast.parse(gen_code)
table_args_map = {}
for node in gen_module.body:
    if isinstance(node, ast.ClassDef):
        table_name = node.name.lower()
        if table_name.endswith('s') and table_name != 'users':
            class_name = node.name[:-1]
        else:
            class_name = node.name
        
        # specific mappings
        mapping = {
            'Users': 'User', 'Books': 'Book', 'Chapters': 'Chapter', 'Assessments': 'Assessment',
            'BookStreaks': 'BookStreak', 'BookUploads': 'BookUpload', 'ProgressSnapshots': 'ProgressSnapshot',
            'Concepts': 'Concept', 'CurriculumPlans': 'CurriculumPlan', 'GraphBuildJobs': 'GraphBuildJob',
            'SourceChunks': 'SourceChunk', 'ConceptEdges': 'ConceptEdge', 'GraphVersions': 'GraphVersion',
            'UserBooks': 'UserBook', 'ContentCompletions': 'ContentCompletion', 'LearningStreaks': 'LearningStreak',
            'LessonSessions': 'LessonSession', 'MasteryEvents': 'MasteryEvent', 'Notifications': 'Notification',
            'TutorInteractions': 'TutorInteraction', 'AssessmentOutcomes': 'AssessmentOutcome',
            'AssessmentResponses': 'AssessmentResponse', 'ConceptChunks': 'ConceptChunk',
            'ConceptFsrs': 'ConceptFSRS', 'ConceptMastery': 'ConceptMastery', 'FsrsReviews': 'FSRSReview',
            'GeneratedQuestions': 'GeneratedQuestion', 'EvaluatedPairs': 'EvaluatedPair',
            'RelationshipCandidates': 'RelationshipCandidate', 'UserConceptState': 'UserConceptState',
            'LearningDna': 'LearningDNA', 'RawConcepts': 'RawConcept'
        }
        if node.name in mapping:
            class_name = mapping[node.name]

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if getattr(target, 'id', '') == '__table_args__':
                        src = ast.get_source_segment(gen_code, item.value)
                        # ensure proper import references (e.g. Index needs to be imported)
                        table_args_map[class_name] = src

files = glob.glob('backend/app/models/*.py')
for fpath in files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    out_content = content
    for class_name, t_args in table_args_map.items():
        # Match class declaration, __tablename__, and optional __table_args__
        # Using a very safe substitution by looking for __tablename__
        pattern = r'(class ' + class_name + r'\([^)]+\):[\s\n]+__tablename__\s*=\s*[\'"][^\'"]+[\'"]\n)(?:    __table_args__\s*=\s*(?:\([^\)]+\)|{.*?})\n)?'
        # The above pattern might fail if __table_args__ contains parenthesis. Let's use a non-greedy dotall approach for table args
        pattern2 = r'(class ' + class_name + r'\([^)]+\):[\s\n]+__tablename__\s*=\s*[\'"][^\'"]+[\'"]\n)(?:    __table_args__\s*=\s*[\s\S]*?\n\n|    __table_args__\s*=\s*[\s\S]*?\n    [a-zA-Z_]+\s*:)?'
        
        # ACTUALLY, it's easier to just find `__tablename__ = '...'` and append `__table_args__` if it doesn't exist,
        # OR replace existing `__table_args__ = (...)`
        def repl(m):
            return m.group(1) + '    __table_args__ = ' + t_args.replace('\n', '\n    ') + '\n\n    # columns follow\n    '
            
        # simpler approach: just find `__tablename__ = 'name'`
        # and insert `__table_args__` right after it
        # BUT we must remove the OLD `__table_args__` if it exists.
        
        # Let's clean out any old __table_args__ first
        old_args_pattern = r'(class ' + class_name + r'\([^)]+\):[\s\n]+__tablename__\s*=\s*[\'"][^\'"]+[\'"]\n)(\s*__table_args__\s*=\s*\([^)]+\)\n)?'
        
        # Let's just do a manual string processing for safety
        lines = out_content.split('\n')
        new_lines = []
        in_target_class = False
        in_table_args = False
        skip_lines = 0
        for i, line in enumerate(lines):
            if skip_lines > 0:
                skip_lines -= 1
                continue
            
            if line.startswith(f'class {class_name}('):
                in_target_class = True
            
            if in_target_class and line.strip().startswith('__tablename__ ='):
                new_lines.append(line)
                
                # Check if next lines are __table_args__
                j = i + 1
                while j < len(lines) and lines[j].strip() == '':
                    j += 1
                if j < len(lines) and lines[j].strip().startswith('__table_args__'):
                    # skip until closing parenthesis
                    open_parens = 0
                    for k in range(j, len(lines)):
                        open_parens += lines[k].count('(') - lines[k].count(')')
                        if open_parens <= 0 and k >= j:
                            skip_lines = k - i
                            break
                            
                # Insert the new table args
                new_lines.append('    __table_args__ = ' + t_args.replace('\n', '\n    '))
                in_target_class = False
                continue
                
            new_lines.append(line)
        out_content = '\n'.join(new_lines)
        
    if out_content != content:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(out_content)
        print(f'Patched {fpath}')
