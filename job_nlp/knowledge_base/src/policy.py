"""Versioned, inspectable analyst proposals. Never an official crosswalk or trained classifier."""
import re, unicodedata

VERSION = 'IT_KB_2.7.0_REMOVE_GENERIC_LEAVES'

def norm(text):
    text = unicodedata.normalize('NFKC', str(text)).casefold()
    return re.sub(r'\s+', ' ', text.replace('–','-').replace('‑','-').replace('™','').replace('®','')).strip()

def title_norm(text):
    text=norm(text)
    for pattern,replacement in [(r'\bback[ -]?end\b','backend'),(r'\bfront[ -]?end\b','frontend'),(r'\bfull[ -]?stack\b','fullstack'),(r'\bdev[ -]?ops\b','devops')]:
        text=re.sub(pattern,replacement,text)
    return text

# Each parent is a job-domain class. Technology product names are not occupation leaves.
TREE = {
 'SOFTWARE': ('Software Engineering', {
  'SOFTWARE_DEVELOPMENT': ('Software Development', 'Design and build software applications and system software.', {
   'FRONTEND_DEVELOPER':'Frontend Developer', 'BACKEND_DEVELOPER':'Backend Developer', 'FULLSTACK_DEVELOPER':'Full-stack Developer', 'ANDROID_DEVELOPER':'Android Developer', 'IOS_DEVELOPER':'iOS Developer', 'DESKTOP_DEVELOPER':'Desktop Application Developer', 'SYSTEMS_PROGRAMMER':'Systems Programmer', 'SOFTWARE_ARCHITECT':'Software Architect', 'CLOUD_SOFTWARE_DEVELOPER':'Cloud Software Developer'}),
  'SPECIALIZED_DEVELOPMENT': ('Specialized Software Development', 'Develop software for specific technical platforms or execution environments.', {
   'EMBEDDED_DEVELOPER':'Embedded Software Developer','IOT_DEVELOPER':'IoT Developer','GAME_DEVELOPER':'Game Developer','BLOCKCHAIN_DEVELOPER':'Blockchain Developer','RPA_DEVELOPER':'RPA Developer'}),
  'SOFTWARE_TESTING': ('Software Quality and Testing', 'Verify software behavior, quality, performance, accessibility and integration.', {
   'SOFTWARE_TESTER':'Software Test Engineer','TEST_AUTOMATION':'Test Automation Engineer','PERFORMANCE_TESTER':'Performance Test Engineer','ACCESSIBILITY_TESTER':'Accessibility Tester','USABILITY_TESTER':'Usability Tester','INTEGRATION_TESTER':'Integration Test Engineer','GAME_TESTER':'Game Tester','LOCALIZATION_TESTER':'Localization Tester'})}),
 'DATA_AI': ('Data, Analytics and Artificial Intelligence', {
  'DATA_ENGINEERING': ('Data Engineering', 'Build and operate data pipelines, data models and analytical platforms.', {
   'DATA_ENGINEER':'Data Engineer','DATA_ARCHITECT':'Data Architect','DATA_WAREHOUSE':'Data Warehouse Developer','ANALYTICS_ENGINEER':'Analytics Engineer'}),
  'DATABASE_ENGINEERING': ('Database Engineering', 'Design, develop, integrate and administer databases.', {
   'DATABASE_ADMIN':'Database Administrator','DATABASE_DEVELOPER':'Database Developer','DATABASE_ARCHITECT':'Database Architect','DATABASE_INTEGRATOR':'Database Integrator'}),
  'DATA_ANALYSIS': ('Data Analysis and Business Intelligence', 'Analyze data, build reports and support data-informed decisions.', {
   'DATA_ANALYST':'Data Analyst','BI_ANALYST':'Business Intelligence Analyst','BI_DEVELOPER':'Business Intelligence Developer','DATA_QUALITY':'Data Quality Specialist'}),
  'AI_ENGINEERING': ('AI and Machine Learning Engineering', 'Engineer AI systems and deploy machine learning applications.', {
   'AI_ENGINEER':'Artificial Intelligence Engineer','ML_ENGINEER':'Machine Learning Engineer','NLP_ENGINEER':'Natural Language Processing Engineer','CV_ENGINEER':'Computer Vision Engineer','KNOWLEDGE_ENGINEER':'Knowledge Engineer'}),
  'DATA_SCIENCE_RESEARCH': ('Data Science and Computing Research', 'Develop statistical models, computational methods and scientific computing research.', {
   'DATA_SCIENTIST':'Data Scientist','ML_RESEARCHER':'Machine Learning Research Scientist','COMPUTER_SCIENTIST':'Computer Research Scientist'})}),
 'PLATFORM_INFRASTRUCTURE': ('Cloud, Platforms and IT Operations', {
  'CLOUD_ENGINEERING': ('Cloud Engineering', 'Design, deploy and operate cloud infrastructure and services.', {
   'CLOUD_ENGINEER':'Cloud Engineer','CLOUD_ARCHITECT':'Cloud Architect','CLOUD_ADMIN':'Cloud Administrator'}),
  'DEVOPS_PLATFORM': ('DevOps and Platform Engineering', 'Automate software delivery and operate reliable developer platforms.', {
   'DEVOPS_ENGINEER':'DevOps Engineer','SRE':'Site Reliability Engineer','PLATFORM_ENGINEER':'Platform Engineer','RELEASE_ENGINEER':'Release Engineer'}),
  'SYSTEMS_OPERATIONS': ('Systems Administration and Operations', 'Configure, administer and operate computing infrastructure.', {
   'SYSTEM_ADMIN':'Systems Administrator','WEB_ADMIN':'Web Administrator','DATACENTER_OPERATOR':'Data Centre Operator','SYSTEM_CONFIG':'Systems Configuration Specialist','STORAGE_ENGINEER':'Storage Engineer','DISASTER_RECOVERY':'IT Disaster Recovery Specialist'})}),
 'SECURITY': ('Cybersecurity', {
  'SECURITY_OPERATIONS': ('Cybersecurity Operations', 'Monitor cyber threats, respond to incidents and investigate digital evidence.', {
   'SECURITY_ANALYST':'Cybersecurity Analyst','INCIDENT_RESPONDER':'Cyber Incident Responder','THREAT_INTELLIGENCE':'Cyber Threat Intelligence Analyst','DIGITAL_FORENSICS':'Digital Forensics Analyst'}),
  'SECURITY_ENGINEERING': ('Cybersecurity Engineering', 'Design and implement technical security controls and architectures.', {
   'SECURITY_ENGINEER':'Security Engineer','SECURITY_ARCHITECT':'Security Architect','APPSEC_ENGINEER':'Application Security Engineer','CLOUD_SECURITY':'Cloud Security Engineer','NETWORK_SECURITY':'Network Security Engineer','EMBEDDED_SECURITY':'Embedded and IoT Security Engineer','IAM_ENGINEER':'Identity and Access Management Specialist','CRYPTOGRAPHER':'Cryptography Specialist'}),
  'OFFENSIVE_SECURITY': ('Offensive Security and Security Testing', 'Assess technical attack surfaces and test cyber defenses.', {
   'PENETRATION_TESTER':'Penetration Tester','VULNERABILITY_ANALYST':'Vulnerability Assessment Specialist'}),
  'SECURITY_GOVERNANCE': ('Cybersecurity Governance, Risk and Compliance', 'Manage cyber risk, assurance, privacy and security policy.', {
   'SECURITY_GRC':'Cybersecurity GRC Specialist','IT_AUDITOR':'IT Auditor','SECURITY_CONSULTANT':'Cybersecurity Consultant','SECURITY_MANAGER':'Cybersecurity Manager','CISO':'Chief Information Security Officer','DATA_PRIVACY':'Data Protection and Privacy Specialist'})}),
 'NETWORKS': ('Networks and Telecommunications', {
  'NETWORK_ENGINEERING': ('Computer Network Engineering', 'Design, administer, secure and support computer networks.', {
   'NETWORK_ENGINEER':'Network Engineer','NETWORK_ARCHITECT':'Network Architect','NETWORK_ADMIN':'Network Administrator','NETWORK_SUPPORT':'Network Support Specialist','NETWORK_TECHNICIAN':'Network Technician'}),
  'TELECOM_ENGINEERING': ('Telecommunications Engineering', 'Engineer telecommunications systems and communication networks.', {
   'TELECOM_ENGINEER':'Telecommunications Engineer','TELECOM_ANALYST':'Telecommunications Analyst','TELECOM_TECHNICIAN':'Telecommunications Technician'})}),
 'ARCHITECTURE_ANALYSIS': ('IT Architecture and Systems Analysis', {
  'SYSTEMS_ARCHITECTURE': ('Enterprise and Systems Architecture', 'Design system architectures and integrate enterprise technology.', {
   'ENTERPRISE_ARCHITECT':'Enterprise Architect','SOLUTION_ARCHITECT':'Solution Architect','SYSTEMS_ARCHITECT':'Systems Architect','SYSTEMS_ENGINEER':'Computer Systems Engineer','INTEGRATION_ENGINEER':'Systems Integration Engineer'}),
  'SYSTEMS_ANALYSIS': ('Business and Systems Analysis', 'Analyze business needs and translate them into information-system requirements.', {
   'BUSINESS_ANALYST':'IT Business Analyst','SYSTEMS_ANALYST':'Systems Analyst','REQUIREMENTS_ENGINEER':'Software Requirements Engineer','IT_CONSULTANT':'IT Consultant'})}),
 'IT_DELIVERY': ('IT Leadership and Delivery', {
  'IT_MANAGEMENT': ('IT and Engineering Management', 'Lead IT strategy, engineering teams, technology operations and resources.', {
   'CIO':'Chief Information Officer','CTO':'Chief Technology Officer','CDO':'Chief Data Officer','ENGINEERING_MANAGER':'Software Engineering Manager','IT_MANAGER':'IT Manager','IT_OPERATIONS_MANAGER':'IT Operations Manager','DATA_MANAGER':'Data and Analytics Manager'}),
  'AGILE_PRODUCT_AND_PROJECT_DELIVERY': ('Agile Product and Project Delivery', 'Plan and coordinate technology products, projects and agile delivery.', {
   'IT_PROJECT_MANAGER':'IT Project Manager','IT_PRODUCT_MANAGER':'IT Product Manager','SCRUM_MASTER':'Scrum Master'}),
  'SERVICE_GOVERNANCE': ('IT Service Governance', 'Manage IT service delivery, change, knowledge, sustainability and supplier relationships.', {
   'SERVICE_DELIVERY_MANAGER':'IT Service Delivery Manager','CHANGE_CONFIG_MANAGER':'IT Change and Configuration Manager','IT_KNOWLEDGE_MANAGER':'IT Knowledge Manager','SUSTAINABLE_IT':'Sustainable IT Specialist','IT_QA_MANAGER':'IT Quality Assurance Manager'})}),
 'SUPPORT': ('IT Support', {
  'USER_APPLICATION_SUPPORT': ('User and Application Support', 'Resolve user computing and software application problems.', {
   'HELPDESK':'IT Help Desk Specialist','DESKTOP_SUPPORT':'Desktop Support Specialist','SUPPORT_ENGINEER':'IT Support Engineer','APPLICATION_SUPPORT':'Application Support Specialist','SUPPORT_MANAGER':'IT Support Manager'}),
  'HARDWARE_SUPPORT': ('Computer Hardware Support', 'Install, diagnose and repair computing devices and peripherals.', {
   'COMPUTER_TECHNICIAN':'Computer Hardware Technician','COMPUTER_REPAIR':'Computer Repair Technician','MOBILE_REPAIR':'Mobile Device Repair Technician'})}),
 'DIGITAL_DESIGN': ('Digital Product Design', {
  'DIGITAL_EXPERIENCE': ('Digital Interface and User Experience', 'Design and evaluate digital interfaces and interactive experiences.', {
   'UI_DESIGNER':'User Interface Designer','UX_DESIGNER':'User Experience Designer','UX_RESEARCHER':'User Experience Researcher','WEB_DESIGNER':'Web Designer','GAME_DESIGNER':'Digital Game Designer'})}),
 'COMPUTER_HARDWARE': ('Computer Hardware Engineering', {
  'HARDWARE_ENGINEERING': ('Computing Hardware Engineering', 'Design and test computer hardware and embedded computing systems.', {
   'HARDWARE_ENGINEER':'Computer Hardware Engineer','HARDWARE_TEST':'Computer Hardware Test Technician','EMBEDDED_DESIGNER':'Embedded System Designer'})}),
 'SPECIALIZED_IT': ('Specialized Informatics', {
  'DOMAIN_INFORMATICS': ('Domain-specific Informatics', 'Apply computing to geospatial, biomedical or healthcare problems; require explicit IT evidence.', {
   'GIS_SPECIALIST':'Geographic Information Systems Specialist','BIOINFORMATICS':'Bioinformatics Specialist','HEALTH_INFORMATICS':'Health Informatics Specialist'})}),
 'IT_ENABLEMENT': ('IT Documentation, Learning and Advisory', {
  'TECHNICAL_ENABLEMENT': ('Technical Documentation and Learning', 'Explain IT systems, train users and support technical adoption.', {
   'TECHNICAL_WRITER':'IT Technical Writer','IT_TRAINER':'IT Trainer','TECHNICAL_ACCOUNT':'IT Technical Account Specialist'})})
}
LEAF_PARENT = {l:p for f,(_,ps) in TREE.items() for p,(_,_,ls) in ps.items() for l in ls}
PARENT_FAMILY = {p:f for f,(_,ps) in TREE.items() for p in ps}
CONDITIONAL_LEAVES = {'GIS_SPECIALIST','BIOINFORMATICS','HEALTH_INFORMATICS','TECHNICAL_ACCOUNT'}

# Reviewed refinements keep management, administration and engineering technicians distinct.
TREE['SECURITY'][1]['SECURITY_ENGINEERING'][2]['SECURITY_ADMIN']='Security Administrator'
TREE['IT_DELIVERY'][1]['IT_MANAGEMENT'][2].update({'BUSINESS_ANALYSIS_MANAGER':'IT Business Analysis Manager','IT_RESEARCH_MANAGER':'IT Research Manager','DIGITAL_TRANSFORMATION_MANAGER':'Digital Transformation Manager'})
TREE['NETWORKS'][1]['TELECOM_ENGINEERING'][2]['TELECOM_MANAGER']='Telecommunications Manager'
TREE['IT_ENABLEMENT'][1]['TECHNICAL_ENABLEMENT'][2]['DOCUMENTATION_MANAGER']='IT Documentation Manager'
TREE['COMPUTER_HARDWARE'][1]['HARDWARE_ENGINEERING'][2]['HARDWARE_ENG_TECHNICIAN']='Computer Hardware Engineering Technician'
# The canonical runtime taxonomy exposes eight technical families only. The
# historical cross-functional families are merged at parent level so a source
# rebuild cannot recreate the retired top-level family IDs.
_RETIRED_FAMILY_TARGETS = {
    'DIGITAL_DESIGN': 'SOFTWARE',
    'IT_DELIVERY': 'PLATFORM_INFRASTRUCTURE',
    'IT_ENABLEMENT': 'SUPPORT',
    'SPECIALIZED_IT': 'DATA_AI',
}
for _retired, _target in _RETIRED_FAMILY_TARGETS.items():
    _entry = TREE.pop(_retired, None)
    if _entry:
        TREE[_target][1].update(_entry[1])
# Project/product delivery is software-product work; keep service/IT
# management under platform infrastructure.
_project_product = TREE['PLATFORM_INFRASTRUCTURE'][1].pop('AGILE_PRODUCT_AND_PROJECT_DELIVERY', None)
if _project_product:
    TREE['SOFTWARE'][1]['AGILE_PRODUCT_AND_PROJECT_DELIVERY'] = _project_product
# Cloud engineering and DevOps/platform engineering are one production
# cloud-platform domain. Keep all functional leaves and expose one parent ID.
_cloud_entry = TREE['PLATFORM_INFRASTRUCTURE'][1].pop('CLOUD_ENGINEERING', None)
_devops_entry = TREE['PLATFORM_INFRASTRUCTURE'][1].pop('DEVOPS_PLATFORM', None)
_cloud_leaves = {}
if _cloud_entry:
    _cloud_leaves.update(_cloud_entry[2])
if _devops_entry:
    _cloud_leaves.update(_devops_entry[2])
if _cloud_leaves:
    TREE['PLATFORM_INFRASTRUCTURE'][1]['CLOUD_AND_PLATFORM'] = (
        'Cloud and Platform Engineering',
        'Design, build and operate cloud platforms, DevOps delivery systems, SRE and release infrastructure.',
        _cloud_leaves,
    )
TREE['PLATFORM_INFRASTRUCTURE'][1].pop('OPERATIONAL_TECHNOLOGY', None)
for _leaf in {'TELECOM_INSTALLER_REPAIRER','TELECOM_TECHNICIAN','TELECOM_OPERATOR','MOBILE_REPAIR','COMPUTER_REPAIR'}:
    for _family, (_family_label, _parents) in TREE.items():
        for _parent, (_parent_label, _parent_definition, _leaves) in _parents.items():
            _leaves.pop(_leaf, None)
_POSITION_LEAVES = {
    'CTO','CIO','CDO','CISO','ENGINEERING_MANAGER','DATA_MANAGER',
    'SECURITY_MANAGER','IT_OPERATIONS_MANAGER','SUPPORT_MANAGER',
    'TELECOM_MANAGER','IT_QA_MANAGER','BUSINESS_ANALYSIS_MANAGER',
    'DOCUMENTATION_MANAGER','IT_RESEARCH_MANAGER','IT_MANAGER',
    'DIGITAL_TRANSFORMATION_MANAGER','SERVICE_DELIVERY_MANAGER',
    'CHANGE_CONFIG_MANAGER','IT_KNOWLEDGE_MANAGER',
}
for _leaf in _POSITION_LEAVES:
    for _family, (_family_label, _parents) in TREE.items():
        for _parent, (_parent_label, _parent_definition, _leaves) in _parents.items():
            _leaves.pop(_leaf, None)
for _family, (_family_label, _parents) in TREE.items():
    for _parent in [p for p, (_, _, leaves) in _parents.items() if not leaves]:
        _parents.pop(_parent, None)

# Remove the two single-leaf parents without discarding their distinct
# functional leaves. Sustainable IT is an infrastructure-efficiency role;
# computer hardware technicians are part of end-user/device support.
_service = TREE['PLATFORM_INFRASTRUCTURE'][1].pop('SERVICE_GOVERNANCE', None)
if _service and 'SUSTAINABLE_IT' in _service[2]:
    TREE['PLATFORM_INFRASTRUCTURE'][1]['SYSTEMS_OPERATIONS'][2]['SUSTAINABLE_IT'] = _service[2]['SUSTAINABLE_IT']
_hardware_support = TREE['SUPPORT'][1].pop('HARDWARE_SUPPORT', None)
if _hardware_support and 'COMPUTER_TECHNICIAN' in _hardware_support[2]:
    TREE['SUPPORT'][1]['USER_APPLICATION_SUPPORT'][2]['COMPUTER_TECHNICIAN'] = _hardware_support[2]['COMPUTER_TECHNICIAN']

# Generic data/systems sinks intentionally remain absent: the resolver may
# return the family and parent while leaving the leaf unresolved.
for _generic_leaf in {'DATA_SPECIALIST_GENERAL', 'SYSTEMS_SPECIALIST_GENERAL', 'COMPUTER_PROGRAMMER'}:
    for _family, (_family_label, _parents) in TREE.items():
        for _parent, (_parent_label, _parent_definition, _leaves) in _parents.items():
            _leaves.pop(_generic_leaf, None)

# These source-backed functional leaves were added by the reviewed KB
# enrichment migration.  Keep the policy catalogue in lock-step with the
# relational database.  Generic APPLICATION_DEVELOPER was retired because it
# acted as an ambiguity sink; generic titles remain parent-only and explicit
# titles are routed to narrower surviving leaves.
TREE['PLATFORM_INFRASTRUCTURE'][1]['SYSTEMS_OPERATIONS'][2]['COMPUTER_OPERATOR'] = 'Computer and Systems Operator'
TREE['DATA_AI'][1]['DATA_ENGINEERING'][2]['DATA_GOVERNANCE_SPECIALIST'] = 'Data Governance and Stewardship Specialist'
TREE['SUPPORT'][1]['TECHNICAL_ENABLEMENT'][2]['DOCUMENT_MANAGEMENT_SPECIALIST'] = 'Digital Document Management Specialist'
TREE['SECURITY'][1]['SECURITY_GOVERNANCE'][2]['IT_COMPLIANCE_SPECIALIST'] = 'IT Compliance Specialist'
if set(TREE) != {'ARCHITECTURE_ANALYSIS','COMPUTER_HARDWARE','DATA_AI','NETWORKS','PLATFORM_INFRASTRUCTURE','SECURITY','SOFTWARE','SUPPORT'}:
    raise RuntimeError(f'canonical family set drifted: {sorted(TREE)}')
LEAF_PARENT = {l:p for f,(_,ps) in TREE.items() for p,(_,_,ls) in ps.items() for l in ls}
PARENT_FAMILY = {p:f for f,(_,ps) in TREE.items() for p in ps}

# Higher-priority patterns express a more specific occupational activity, not a product.
# They generate reviewable taxonomy proposals; they do not change skill extraction rules.
RULE_SPECS = [
 ('CISO',r'chief (?:ict |information |cyber ?)?security officer',130),
 ('CIO',r'chief information officer|\bcio\b',130),('CTO',r'chief (?:technology|technical) officer|\bcto\b',130),('CDO',r'chief data officer|\bcdo\b',130),
 ('INCIDENT_RESPONDER',r'(?:cyber|security|digital).*incident|incident (?:response|responder|handler)',120),
 ('DIGITAL_FORENSICS',r'(?:digital|computer|cyber).*forensic|forensic.*(?:digital|computer|cyber)',120),
 ('THREAT_INTELLIGENCE',r'(?:cyber|threat).*intel|threat (?:hunter|hunting|investigat)',120),
 ('PENETRATION_TESTER',r'penetration|pentest|ethical hack|bug bounty|red team|offensive (?:cyber|security)|security hacker',120),
 ('VULNERABILITY_ANALYST',r'vulnerabilit|(?:cyber|security|secure software|network security|system security).*?(?:test|assess)',118),
 ('IAM_ENGINEER',r'identity|\biam\b|access management',117),
 ('APPSEC_ENGINEER',r'application security|secure software (?:develop|engineer)|software security',115),
 ('CLOUD_SECURITY',r'cloud security',115),('NETWORK_SECURITY',r'network security (?:engineer|admin)',115),
 ('EMBEDDED_SECURITY',r'(?:embedded|iot|internet of things|automotive|mobile|scada).*security',116),
 ('SECURITY_ARCHITECT',r'security architect',116),('CRYPTOGRAPHER',r'cryptograph|cryptanalyst',115),
 ('SECURITY_GRC',r'(?:cyber|security).*(?:governance|risk|compliance|policy)|compliance.*information security',114),
 ('IT_AUDITOR',r'\bit audit|\bict audit|systems auditor.*ict',114),('DATA_PRIVACY',r'data (?:protection|privacy)|privacy.*(?:data|information)',114),
 ('SECURITY_CONSULTANT',r'(?:ict|cyber).*security.*(?:consult|advice)|consultant.*ict security',112),
 ('SECURITY_MANAGER',r'(?:cyber|computer|ict|information|network|web).*security (?:manager|director|coordinator)|chief ict security',110),
 ('SECURITY_ENGINEER',r'(?:cyber|information|computer|ict).*security.*(?:engineer|develop)|cyber defense infrastructure',108),
 ('SECURITY_ADMIN',r'(?:ict|information|computer|cyber).*security administrator',118),
 ('SECURITY_ANALYST',r'(?:cyber|information security|network defense|network security|ict security).*analyst|blue team|cyber defender',90),
 ('LOCALIZATION_TESTER',r'locali[sz].*(?:test|quality assurance)',117),('GAME_TESTER',r'(?:games?|gaming).*test|test.*(?:games?|gaming)',116),
 ('ACCESSIBILITY_TESTER',r'accessibility.*test',115),('USABILITY_TESTER',r'usability.*test',115),('PERFORMANCE_TESTER',r'performance.*test',115),
 ('INTEGRATION_TESTER',r'integration.*test',115),('TEST_AUTOMATION',r'(?:test|quality assurance|qa).*automat|automat.*(?:test|quality assurance|qa)',115),
 ('SOFTWARE_TESTER',r'(?:software|application|ict|systems?).*(?:test|quality assurance|quality control|quality engineer)|beta tester',100),
 ('IT_QA_MANAGER',r'ict quality assurance manager|software quality.*manager',125),
 ('FRONTEND_DEVELOPER',r'front[ -]?end|user interface develop|\bui programmer|react[.]?js developer|angularjs developer',110),
 ('BACKEND_DEVELOPER',r'back[ -]?end',110),('FULLSTACK_DEVELOPER',r'full[ -]?stack',112),
 ('ANDROID_DEVELOPER',r'android develop',112),('IOS_DEVELOPER',r'\bios develop',112),
 ('DESKTOP_DEVELOPER',r'desktop.*develop|windows software engineer',105),('SYSTEMS_PROGRAMMER',r'operating systems?.*(?:develop|program|design)|mainframe program|systems? programmer',105),
 ('SOFTWARE_ARCHITECT',r'software architect|application architect|java architect',105),
 ('CLOUD_SOFTWARE_DEVELOPER',r'cloud (?:software|native).*?(?:develop|engineer)|cloud developer',110),
 ('EMBEDDED_DEVELOPER',r'embedded.*(?:software|develop)|(?:battery|satellite|drone|smart home).*software|firmware',111),
 ('IOT_DEVELOPER',r'(?:iot|internet of things).*develop',110),
 ('GAME_DEVELOPER',r'(?:games?|gaming).*?(?:develop|program|engineer)|(?:games?|gaming) creator',100),
 ('BLOCKCHAIN_DEVELOPER',r'blockchain.*(?:develop|engineer|architect)',105),('RPA_DEVELOPER',r'\brpa\b|robotic process automation',110),
 ('DATA_ARCHITECT',r'(?:big )?data architect',110),('DATA_ENGINEER',r'data engineer|data visualization developer|hadoop developer|datastage developer|etl developer',105),
 ('DATA_WAREHOUSE',r'data warehous',110),('ANALYTICS_ENGINEER',r'analytics engineer',110),
 ('DATABASE_ADMIN',r'database admin|data ?base administrator|\bdba\b',108),('DATABASE_DEVELOPER',r'database develop',108),
 ('DATABASE_ARCHITECT',r'database (?:architect|designer)|data ?base designer',108),('DATABASE_INTEGRATOR',r'database integrat',108),
 ('DATA_QUALITY',r'data quality',108),('BI_DEVELOPER',r'(?:business intelligence|\bbi\b).*?(?:develop|engineer)|tableau developer',108),
 ('BI_ANALYST',r'business intelligence|\bbi consultant|\bbi specialist',100),
 ('DATA_ANALYST',r'data analyst|data analytics|data min(?:er|ing)|information analyst|analytics (?:consultant|associate)',90),
 ('CV_ENGINEER',r'computer vision',110),('NLP_ENGINEER',r'natural language|\bnlp\b|computational linguist|language engineer',110),
 ('ML_RESEARCHER',r'machine learning.*scientist',111),('ML_ENGINEER',r'machine learning.*(?:engineer|develop|designer)',110),
 ('AI_ENGINEER',r'artificial intelligence|\bai (?:engineer|specialist|system|designer|consultant|technician)',100),('KNOWLEDGE_ENGINEER',r'knowledge engineer|intelligent systems? (?:develop|engineer|designer)',102),
 ('DATA_SCIENTIST',r'data scientist|predictive model',100),('COMPUTER_SCIENTIST',r'computer scientist|computer and information research scientist|computational scientist|ict research consultant',100),
 ('SRE',r'site reliability',118),('DEVOPS_ENGINEER',r'dev[ -]?ops',112),('PLATFORM_ENGINEER',r'platform engineer',108),('RELEASE_ENGINEER',r'release engineer|build engineer',108),
 ('CLOUD_ARCHITECT',r'cloud.*architect',105),('CLOUD_ADMIN',r'cloud administrator',107),('CLOUD_ENGINEER',r'cloud|cloud-native',80),
 ('DISASTER_RECOVERY',r'ict disaster recovery|ict resilience',110),('DATACENTER_OPERATOR',r'data cent(?:er|re)|computer operator|computer operations technician|computer console operator',105),
 ('WEB_ADMIN',r'webmaster|web administrator|websphere administrator|web.*(?:operations|technologies administrator)|website manager',110),
 ('SYSTEM_CONFIG',r'system configur|application configur|app configur|application.*packag|system setup',105),
 ('STORAGE_ENGINEER',r'storage engineer|storage administrator',105),
 ('SYSTEM_ADMIN',r'(?:systems?|windows|mainframe|network and computer systems).*admin',95),
 ('NETWORK_ARCHITECT',r'network architect|network designer|internet architect',105),('NETWORK_ADMIN',r'network admin|(?:local|wide) area network administrator|\blan admin|\bwan admin',105),
 ('NETWORK_SUPPORT',r'network.*support|network diagnostic|\blan support|\bwan support',100),
 ('NETWORK_ENGINEER',r'network.*engineer|internetwork.*expert|\bwan engineer|\bnoc engineer|network and systems engineer',98),
 ('NETWORK_TECHNICIAN',r'network.*technician|network operations|network configur|network specialist|network analyst|internetworking technician',85),
 ('TELECOM_ANALYST',r'telecommunications? analyst|telecommunication design analyst',102),
 ('TELECOM_ENGINEER',r'telecom.*(?:engineer|design|architect)|communications engineer',95),
 ('TELECOM_TECHNICIAN',r'telecom.*(?:technician|installer|repairer)|broadband.*technician|cabl(?:e|ing).*technician|radiocommunications technician|wireless.*technician',60),
 ('TELECOM_MANAGER',r'telecommunications? manager|aviation data communications manager',130),
 ('ENTERPRISE_ARCHITECT',r'enterprise architect',110),('SOLUTION_ARCHITECT',r'solutions? architect',105),
 ('INTEGRATION_ENGINEER',r'integration (?:engineer|consultant)|systems? integrat|application integrat|cross enterprise integrat',103),
 ('SYSTEMS_ARCHITECT',r'systems? architect|computer architect|technical architect',95),('SYSTEMS_ENGINEER',r'computer systems? engineer|ict system engineer',95),
 ('BUSINESS_ANALYST',r'business (?:systems? |information |ict )?analyst|ict business analys',95),
 ('REQUIREMENTS_ENGINEER',r'requirements? (?:engineer|analyst|planner)|software requirement',105),
 ('SYSTEMS_ANALYST',r'systems? analys|software analyst|computer analyst|application analyst',90),('IT_CONSULTANT',r'ict consultant|computer consultant|business technology consultant|information technology consultant',90),
 ('BUSINESS_ANALYSIS_MANAGER',r'ict business analysis manager',130),('IT_RESEARCH_MANAGER',r'ict research manager',130),('DIGITAL_TRANSFORMATION_MANAGER',r'digital transformation manager',130),('DOCUMENTATION_MANAGER',r'ict documentation manager',130),
 ('DATA_MANAGER',r'(?:data|analytics|business intelligence).*manager',125),
 ('ENGINEERING_MANAGER',r'(?:software|application|system) (?:development |engineering |programming )?(?:manager|director|supervisor)',122),
 ('IT_OPERATIONS_MANAGER',r'(?:ict|it|computer).*operations (?:manager|supervisor)|ict operations manager',120),
 ('IT_MANAGER',r'(?:ict|information technology|information systems|computer and information systems|mis) (?:manager|director)',80),
 ('IT_PROJECT_MANAGER',r'(?:ict|it|information technology|computer|web|internet|network|telecommunications).*project|project management it specialist',125),
 ('IT_PRODUCT_MANAGER',r'(?:ict|it|cloud|software).*product',125),('SCRUM_MASTER',r'scrum master',125),
 ('SERVICE_DELIVERY_MANAGER',r'ict service delivery|it service delivery',125),('CHANGE_CONFIG_MANAGER',r'ict change and configuration|configuration management',115),
 ('IT_KNOWLEDGE_MANAGER',r'ict information and knowledge|ict knowledge|cyber it knowledge',120),('SUSTAINABLE_IT',r'green (?:ict|it)|(?:ict|it) environmental|sustainable (?:it|ict|systems?)|(?:ict|it) sustainability',120),
 ('SUPPORT_MANAGER',r'(?:support|help desk) manager',120),('APPLICATION_SUPPORT',r'application support|software support|application customer service',103),
 ('DESKTOP_SUPPORT',r'desktop support|pc support|work station support',105),('HELPDESK',r'help ?desk|service desk',105),
 ('SUPPORT_ENGINEER',r'(?:ict|it|computer|technical|systems?|user).*support|technical support',85),
 ('MOBILE_REPAIR',r'mobile.*(?:repair|technician|maintain)|mobile phone repair',108),
 ('COMPUTER_REPAIR',r'(?:computer|pc).*repair|computer mechanic|computer service technician|break/fix',107),
 ('COMPUTER_TECHNICIAN',r'computer.*(?:technician|installer)|ict technician|ict hardware technician|it hardware|pc hardware technician',90),
 ('HARDWARE_ENG_TECHNICIAN',r'computer hardware engineering technician',119),('HARDWARE_TEST',r'computer hardware.*(?:test|inspect)',114),('HARDWARE_ENGINEER',r'computer hardware.*(?:engineer|design|develop)|pc hardware engineer',110),('EMBEDDED_DESIGNER',r'embedded.*(?:system|hardware|electronics).*(?:designer|design)|microcontroller.*(?:hardware|design)|pcb.*(?:design|layout)',110),
 ('UX_RESEARCHER',r'(?:ux|user experience).*research',115),('UX_DESIGNER',r'\bux\b|user experience|usability developer',100),
 ('UI_DESIGNER',r'user interface.*(?:design|architect)|\bui (?:design|product)',100),('WEB_DESIGNER',r'web.*design|website designer',95),('GAME_DESIGNER',r'(?:games?|gambling).*design',98),
 ('GIS_SPECIALIST',r'geographic information|geospatial|\bgis\b',119),('BIOINFORMATICS',r'bioinformatic',119),('HEALTH_INFORMATICS',r'health informatic|clinical information systems|nursing informatic|picture archiving|\bpacs\b|pathology ict',119),
 ('TECHNICAL_WRITER',r'api writer|technical communicator|information developer|ict documentation',100),('IT_TRAINER',r'ict train|ict teacher|ict tutor|applications? trainer|systems? trainer',100),('TECHNICAL_ACCOUNT',r'ict account manager|ict vendor relationship',100),
]
_REMOVED_NONCORE_LEAVES = {
    'TELECOM_INSTALLER_REPAIRER', 'TELECOM_TECHNICIAN', 'TELECOM_OPERATOR',
    'MOBILE_REPAIR', 'COMPUTER_REPAIR',
    'SECURITY_SPECIALIST_GENERAL', 'TELECOM_SPECIALIST_GENERAL',
    'IT_GENERALIST', 'WEB_DEVELOPER', 'MOBILE_DEVELOPER',
    'APPLICATION_DEVELOPER',
}
RULE_SPECS = [row for row in RULE_SPECS if row[0] not in (_REMOVED_NONCORE_LEAVES | _POSITION_LEAVES)]
RULES = [(leaf,re.compile(pattern,re.I),priority) for leaf,pattern,priority in RULE_SPECS]
GENERIC_PARENTS = [
 ('SOFTWARE_DEVELOPMENT',r'develop|programmer|software engineer|software specialist|software designer|app coder'),
 ('DATA_ENGINEERING',r'\bdata (?:specialist|consultant|expert|technician)\b'),
 ('SYSTEMS_ANALYSIS',r'\b(?:computer|information|systems?) systems? specialist\b|\bsystems specialist\b'),
 ('SYSTEMS_OPERATIONS',r'\b(?:it|ict|mis|information systems?|information technology|internet technology|computer and information systems|computer systems information) (?:manager|director|officer)\b|\bcio\b|\bchief information officer\b|\b(?:it|ict) (?:practice|innovation) manager\b'),
 ('SOFTWARE_TESTING',r'\bqa\b|quality assurance|quality analyst.*ict'),
 ('SYSTEMS_OPERATIONS',r'operating systems? specialist|computer operations'),
 ('NETWORK_ENGINEERING',r'network|internetwork'),
 ('SECURITY_OPERATIONS',r'security analyst'),
 ('SECURITY_OPERATIONS',r'cyber|ict security|computer security'),
 ('SECURITY_ENGINEERING',r'security engineer'),
 ('SYSTEMS_ARCHITECTURE',r'systems? engineer|systems? design'),
 ('USER_APPLICATION_SUPPORT',r'support specialist'),
 ('TELECOM_ENGINEERING',r'telecom|broadband'),
]
EXCLUDE_TITLE = re.compile(r'sewerage|wastewater|water network|pipeline network|sheet metal|robot welder|computer numerically controlled|data entry|telecommunication equipment shop|wireless telegrapher|wireless watcher',re.I)
CERT_TITLE = re.compile(r'^(?:certified information systems security professional|certified novell engineer|cisco certified|registered communications distribution designer)|^(?:ccie|ccnp|cissp)$',re.I)
CONDITIONAL_TITLE = re.compile(r'bioinformatic|geographic information|\bgis\b|geospatial|\bpacs\b|health informatic|clinical|nursing|telecom.*(?:cable|line|install|repair|rigger)|cell tower|broadband|cable (?:tv|television)|communications operator|wireless operator|radio.*technician|mobile.*repair',re.I)

def classify(label):
    if EXCLUDE_TITLE.search(label) or CERT_TITLE.search(label): return None
    matches=[(pri,len(m.group()),leaf,m.group()) for leaf,pat,pri in RULES if (m:=pat.search(label))]
    if matches:
        pri,_,leaf,matched=max(matches)
        p=LEAF_PARENT[leaf]
        return {'family_id':PARENT_FAMILY[p],'parent_id':p,'leaf_id':leaf,'rule_id':'label:'+leaf,'matched':matched,'priority':pri}
    if re.search(r'^(?:python|java|javascript|c\+\+|c#|c|[.]net|asp[.]net|cobol|ruby|php)(?: software)? (?:developer|programmer|engineer)',label,re.I):
        return {'family_id':'SOFTWARE','parent_id':'SOFTWARE_DEVELOPMENT','leaf_id':None,'rule_id':'technology_qualified_development_parent','matched':label,'priority':100}
    for p,pat in GENERIC_PARENTS:
        if re.search(pat,label,re.I): return {'family_id':PARENT_FAMILY[p],'parent_id':p,'leaf_id':None,'rule_id':'parent:'+p,'matched':pat,'priority':20}
    return None

# Occupation scope is assessed separately from lexical title matches.
ONET_CORE = {'11-3021.00','17-2061.00','15-2051.00','15-2051.01'}
ONET_CONDITIONAL = {'15-1211.01','15-1299.02','15-1299.03','15-2051.02','15-2099.01','19-1029.01','27-3042.00','49-2011.00','13-1151.00','17-3023.00','49-2022.00','49-9052.00'}
ESCO_CORE_EXTRA = {'telecommunications engineer','telecommunications analyst','computer hardware engineer','computer hardware engineering technician','computer hardware test technician','computer hardware repair technician','ICT trainer','ICT teacher secondary school','ICT research manager','ICT account manager','web designer','digital games designer','language engineer','data protection officer'}
ESCO_CONDITIONAL = {'geographic information systems specialist','bioinformatics scientist','clinical informatics manager','picture archiving and communication systems administrator','telecommunications technician','telecommunications equipment maintainer','communication infrastructure maintainer','mobile devices technician','mobile phone repair technician','technical communicator','big data archive librarian','director of compliance and information security','director of compliance and information security in gambling'}
OSCA_CORE_EXTRA={'113132','113299','223231','223232','223233','223234','223431','242132','242133'}
OSCA_CONDITIONAL={'241233','314132','314133','314134','314135','314199','382332','382333'}
def scope_for(source,native,label,raw):
    if label=='numerical tool and process control programmer':return 'reference_only','Industrial numerical-control programming is outside the default IT scope.'
    if label in {'web content manager','aviation data communications manager'}:return 'conditional','Require explicit IT platform/network responsibilities; not content editing or flight operations alone.'
    if source=='ONET':
        if native in ONET_CONDITIONAL: return 'conditional','Explicit domain-boundary policy; require IT duties in the actual document.'
        if native.startswith('15-12') or native in ONET_CORE:return 'core','Explicit IT O*NET-SOC allowlist.'
    elif source=='ESCO':
        if label in ESCO_CONDITIONAL:return 'conditional','Specialized or adjacent occupation; require IT duties.'
        isco=str(raw.get('iscoGroup',''))
        if isco.startswith('25') or isco.startswith(('3511','3512','3513','3514')) or isco=='1330' or label in ESCO_CORE_EXTRA:
            if label=='search engine optimisation expert':return 'conditional','SEO requires software/data duties; marketing alone is outside IT.'
            return 'core','ICT-specific ISCO group or explicit IT occupation inclusion.'
    elif source=='OSCA':
        if native in OSCA_CONDITIONAL:return 'conditional','Telecom field work or specialized informatics requires IT duties.'
        if native.startswith(('27','11323','22323')) or native in OSCA_CORE_EXTRA or native in {'314131','314136','314231'}:return 'core','Explicit OSCA ICT/data occupation inclusion.'
    return 'reference_only','Retained only as a competing source-title match; no IT profile inheritance.'

# Broad source concepts must not contribute a falsely precise leaf profile.
BROAD_SOURCE_PARENTS = {
 'ICT capacity planner':'SYSTEMS_OPERATIONS','ICT auditor manager':'SECURITY_GOVERNANCE',
 'ICT resilience manager':'SECURITY_GOVERNANCE','ICT research consultant':'DATA_SCIENCE_RESEARCH',
 'ICT security technician':'SECURITY_ENGINEERING','web content manager':'SYSTEMS_OPERATIONS',
 'Cyber Security Operations Coordinator':'SECURITY_OPERATIONS',
 'Software Developers':'SOFTWARE_DEVELOPMENT','Computer Programmers':'SOFTWARE_DEVELOPMENT',
 'Software Engineer':'SOFTWARE_DEVELOPMENT','software developer':'SOFTWARE_DEVELOPMENT','ICT application developer':'SOFTWARE_DEVELOPMENT',
 'Computer and Information Systems Managers':'IT_MANAGEMENT',
 'Network and Computer Systems Administrators':'SYSTEMS_OPERATIONS',
 'Computer Systems Engineers/Architects':'SYSTEMS_ARCHITECTURE',
 'Software Quality Assurance Analysts and Testers':'SOFTWARE_TESTING',
 'Web and Digital Interface Designers':'DIGITAL_EXPERIENCE','UI / UX Designer':'DIGITAL_EXPERIENCE',
 'ICT Network and Systems Engineer':'NETWORK_ENGINEERING',
 'Information Security Engineers':'SECURITY_ENGINEERING','Information Security Analysts':'SECURITY_OPERATIONS',
 'ICT and Telecommunications Technicians nec':'USER_APPLICATION_SUPPORT',
 'Computer, Automated Teller, and Office Machine Repairers':'USER_APPLICATION_SUPPORT',
 'Computer Occupations, All Other':None,
}
def classify_occupation(label):
    if label=='Cyber Security Advice and Assessment Specialist':
        p='SECURITY_GOVERNANCE'
        return {'family_id':PARENT_FAMILY[p],'parent_id':p,'leaf_id':'SECURITY_CONSULTANT','rule_id':'source_description:OSCA_271132','matched':label,'priority':130}
    if label in BROAD_SOURCE_PARENTS:
        p=BROAD_SOURCE_PARENTS[label]
        if p is None:return None
        return {'family_id':PARENT_FAMILY[p],'parent_id':p,'leaf_id':None,'rule_id':'broad_source:'+p,'matched':label,'priority':0}
    return classify(label)

# This is a functional classification proposal, not proof of an occupation or task.
FUNCTIONAL_DOMAINS={
 'SOFTWARE_BUILD':'Software development and build tooling','WEB_UI':'Web and interface development','MOBILE':'Mobile development',
 'DATA_STORAGE':'Databases and data storage','DATA_PIPELINES':'Data integration and streaming','ANALYTICS':'Analytics and reporting',
 'AI_ML':'Artificial intelligence and machine learning','CLOUD':'Cloud infrastructure','DEVOPS':'Deployment and configuration automation',
 'SECURITY':'Security and identity','NETWORKS':'Networking and communications','OBSERVABILITY':'Monitoring and observability',
 'SYSTEMS':'Operating systems and runtime infrastructure','QUALITY':'Software testing and quality','DESIGN':'Digital design and graphics',
 'ENTERPRISE_APPS':'Enterprise application platforms','COLLABORATION':'Collaboration and productivity','IT_SERVICE':'IT support and service management',
 'TECHNICAL_DOCUMENTATION':'Technical documentation and learning','GEOSPATIAL':'Geospatial computing','SPECIALIST_SOFTWARE':'Specialist domain software'
}
CATEGORY_DOMAINS={
 'PROGRAMMING_LANGUAGE':['SOFTWARE_BUILD'],'MARKUP_STYLE_LANGUAGE':['WEB_UI'],'DATA_SERIALIZATION_LANGUAGE':['DATA_PIPELINES'],
 'FRAMEWORK':['SOFTWARE_BUILD'],'LIBRARY':['SOFTWARE_BUILD'],'DEVELOPMENT_TOOL':['SOFTWARE_BUILD'],'IDE_EDITOR':['SOFTWARE_BUILD'],
 'BUILD_TOOL':['SOFTWARE_BUILD'],'PACKAGE_MANAGER':['SOFTWARE_BUILD'],'VERSION_CONTROL':['SOFTWARE_BUILD','DEVOPS'],
 'DATABASE':['DATA_STORAGE'],'SEARCH_ENGINE':['DATA_STORAGE'],'STORAGE':['DATA_STORAGE'],'STREAM_PROCESSING':['DATA_PIPELINES'],
 'MESSAGE_BROKER':['DATA_PIPELINES'],'BI_ANALYTICS':['ANALYTICS'],'AI_ML':['AI_ML'],
 'CLOUD_SERVICE':['CLOUD'],'CLOUD_PLATFORM':['CLOUD'],'CONTAINER':['DEVOPS'],'CONTAINER_ORCHESTRATION':['DEVOPS'],
 'CONFIGURATION_MANAGEMENT':['DEVOPS'],'INFRASTRUCTURE_AS_CODE':['DEVOPS'],'CI_CD':['DEVOPS'],
 'SECURITY_TOOL':['SECURITY'],'IDENTITY_ACCESS':['SECURITY'],'MONITORING_OBSERVABILITY':['OBSERVABILITY'],
 'OPERATING_SYSTEM':['SYSTEMS'],'VIRTUALIZATION':['SYSTEMS'],'RUNTIME':['SYSTEMS'],'APPLICATION_SERVER':['SYSTEMS'],
 'API_TECHNOLOGY':['WEB_UI','DATA_PIPELINES'],'WEB_SERVER':['WEB_UI'],'CMS':['WEB_UI'],'MOBILE_TECHNOLOGY':['MOBILE'],
 'TESTING_TOOL':['QUALITY'],'DESIGN_CAD':['DESIGN'],'ERP_CRM':['ENTERPRISE_APPS'],'PROJECT_ISSUE_TOOL':['COLLABORATION'],
 'COLLABORATION_TOOL':['COLLABORATION']
}
DOMAIN_PATTERNS={
 'SOFTWARE_BUILD':r'develop|programming|compiler|file version|code review|write.*code|debug',
 'WEB_UI':r'web |interface develop|website|api |graphical user interface',
 'MOBILE':r'mobile|smartphone', 'DATA_STORAGE':r'data ?base|storage|backup|archiv|file ?system',
 'DATA_PIPELINES':r'data integrat|data conversion|data pipeline|data warehouse|etl|metadata',
 'ANALYTICS':r'analytic|business intelligence|data analysis|reporting|data mining|spreadsheet|statistical',
 'AI_ML':r'machine learning|neural network|artificial intelligence|expert system|voice recognition|pattern recognition',
 'CLOUD':r'cloud', 'DEVOPS':r'configuration management|deploy|devops|continuous integrat|release.*software',
 'SECURITY':r'secur|virus|authenticat|access control|vulnerabilit|cyber|encrypt',
 'NETWORKS':r'network|communications server|switch or router|routing|telecommunicat',
 'OBSERVABILITY':r'monitor|observab|logging|log analys',
 'SYSTEMS':r'operating system|device driver|system software|server|virtualiz|virtualis',
 'QUALITY':r'program testing|test.*software|software.*test|quality assurance|debug|accessibility|usability',
 'DESIGN':r'graphic|design cad|photo imaging|video creation|web design|digital design',
 'ENTERPRISE_APPS':r'enterprise resource|customer relationship|erp|crm|enterprise application',
 'COLLABORATION':r'project management|electronic mail|office suite|word processing|presentation|calendar|conferenc|instant messag',
 'IT_SERVICE':r'helpdesk|help desk|technical support|support.*user|service desk',
 'TECHNICAL_DOCUMENTATION':r'computer based training|technical document|user manual|train.*users',
 'GEOSPATIAL':r'geographic information|geospatial|map creation',
 'SPECIALIST_SOFTWARE':r'medical software|financial analysis software|accounting software|manufacturing|industrial control|flight control|tax preparation'
}

# Candidate parent domains are weak supporting context, never occupation assignments.
DOMAIN_PARENT_CANDIDATES={
 'SOFTWARE_BUILD':['SOFTWARE_DEVELOPMENT','SPECIALIZED_DEVELOPMENT','SOFTWARE_TESTING'],
 'WEB_UI':['SOFTWARE_DEVELOPMENT','DIGITAL_EXPERIENCE'],
 'MOBILE':['SOFTWARE_DEVELOPMENT','SPECIALIZED_DEVELOPMENT'],
 'DATA_STORAGE':['DATABASE_ENGINEERING','DATA_ENGINEERING','SYSTEMS_OPERATIONS'],
 'DATA_PIPELINES':['DATA_ENGINEERING','DATABASE_ENGINEERING'],
 'ANALYTICS':['DATA_ANALYSIS','DATA_SCIENCE_RESEARCH'],
 'AI_ML':['AI_ENGINEERING','DATA_SCIENCE_RESEARCH'],
 'CLOUD':['CLOUD_AND_PLATFORM','SYSTEMS_OPERATIONS'],
 'DEVOPS':['CLOUD_AND_PLATFORM','SYSTEMS_OPERATIONS'],
 'SECURITY':['SECURITY_ENGINEERING','SECURITY_OPERATIONS','OFFENSIVE_SECURITY','SECURITY_GOVERNANCE'],
 'NETWORKS':['NETWORK_ENGINEERING','TELECOM_ENGINEERING'],
 'OBSERVABILITY':['CLOUD_AND_PLATFORM','SYSTEMS_OPERATIONS','NETWORK_ENGINEERING'],
 'SYSTEMS':['SYSTEMS_OPERATIONS','SYSTEMS_ARCHITECTURE'],
 'QUALITY':['SOFTWARE_TESTING'],
 'DESIGN':['DIGITAL_EXPERIENCE','HARDWARE_ENGINEERING'],
 'ENTERPRISE_APPS':['SYSTEMS_ANALYSIS','SYSTEMS_ARCHITECTURE','USER_APPLICATION_SUPPORT'],
 'COLLABORATION':['AGILE_PRODUCT_AND_PROJECT_DELIVERY'],
 'IT_SERVICE':['USER_APPLICATION_SUPPORT'],
 'TECHNICAL_DOCUMENTATION':['TECHNICAL_ENABLEMENT'],
 'GEOSPATIAL':['DOMAIN_INFORMATICS'],
 'SPECIALIST_SOFTWARE':['DOMAIN_INFORMATICS']
}
