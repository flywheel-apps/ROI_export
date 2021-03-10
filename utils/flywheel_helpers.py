

def get_containers_at_level(fw, container, level):
    try:
        ct = container.container_type
    except Exception:
        ct = 'analysis'
    
    if ct == level:
        return([container])
    
    if level == "acquisition":
        # Expanding To Children
        if ct == "project" or ct == "subject":
            containers = []
            temp_containers = container.sessions()
            for cont in temp_containers:
                containers.extend(cont.acquisitions())
                
        elif ct == 'session':
            containers = container.acquisitions()
            
        # Shrink to parent
        else:
            containers = [get_acquisition(fw, container)]

    elif level == "session":
        # Expanding To Children
        if ct == "project" or 'subject':
            containers = container.sessions()
        
        # Shrink to parent
        else:
            containers = [get_session(fw, container)]

    elif level == "subject":
        # Expanding To Children
        if ct == "project":
            containers = container.subjects()
        
        # Shrink to parent
        else:
            containers = [get_subject(fw, container)]

    elif level == 'analysis':
        containers = container.analyses
    elif level == 'file':
        containers = container.files
    
    return containers
            
 





def get_children(container):

    ct = container.get('container_type', 'analysis')
    if ct == "project":
        children = container.subjects()
    elif ct == "subject":
        children = container.sessions()
    elif ct == "session":
        children = container.acquisitions()
    elif ct == "acquisition" or ct == "analysis":
        children = container.files
    else:
        children = []

    return children


def get_parent(fw, container):

    ct = container.get('container_type', 'analysis')

    if ct == "project":
        parent = fw.get_group(container.group)
    elif ct == "subject":
        parent = fw.get_project(container.project)
    elif ct == "session":
        parent = container.subject
    elif ct == "acquisition":
        parent = container.get_session(container.session)
    elif ct == "analysis":
        parent = fw.get(container.parent["id"])
    elif ct == 'file':
        parent = container.parent.reload()
    else:
        parent = None

    return parent


def get_subject(fw, container):

    ct = container.get('container_type', 'analysis')

    if ct == "project":
        subject = None
    elif ct == "subject":
        subject = container
    elif ct == "session":
        subject = container.subject
    elif ct == "acquisition":
        subject = fw.get_subject(container.parents.subject)
    elif ct == "file":
        subject = get_subject(container.parent.reload())
    elif ct == "analysis":
        sub_id = container.parents.subject
        if sub_id is not None:
            subject = fw.get_subject(sub_id)
        else:
            subject = None

    return subject


def get_session(fw, container):

    ct = container.get('container_type', 'analysis')

    if ct == "project":
        session = None
    elif ct == "subject":
        session = None
    elif ct == "session":
        session = container
    elif ct == "acquisition":
        session = fw.get_session(container.parents.session)
    elif ct == "file":
        session = get_session(container.parent.reload())
    elif ct == "analysis":
        ses_id = container.parents.session
        if ses_id is not None:
            session = fw.get_session(ses_id)
        else:
            session = None

    return session






def get_acquisition(fw, container):
    ct = container.get('container_type', 'analysis')
    
    print(container.container_type)
    
    if ct == "project":
        acquisition = None
    elif ct == "subject":
        acquisition = None
    elif ct == "session":
        acquisition = None
    elif ct == "acquisition":
        acquisition = container
    elif ct == "file":
        acquisition = get_acquisition(container.parent.reload())
    elif ct == "analysis":
        ses_id = container.parents.acquisition
        if ses_id is not None:
            acquisition = fw.get_acquisition(ses_id)
        else:
            acquisition = None

    return acquisition


def get_analysis(fw, container):
    ct = container.get('container_type', 'analysis')

    if ct == "project":
        analysis = None
    elif ct == "subject":
        analysis = None
    elif ct == "session":
        analysis = None
    elif ct == "acquisition":
        analysis = None
    elif ct == "file":
        analysis = get_analysis(container.parent.reload())
    elif ct == "analysis":
        analysis = container

    return analysis


def get_project(fw, container):
    ct = container.get('container_type', 'analysis')

    if ct == "project":
        project = container
    elif ct == "subject":
        project = fw.get_project(container.parents.project)
    elif ct == "session":
        project = fw.get_project(container.parents.project)
    elif ct == "acquisition":
        project = fw.get_project(container.parents.project)
    elif ct == "file":
        project = get_project(container.parent.reload())
    elif ct == "analysis":
        project = fw.get_project(container.parents.project)

    return project


def get_parent_at_level(fw, container, level):

    if level == "project":
        parent = get_project(fw, container)
    elif level == "subject":
        parent = get_subject(fw, container)
    elif level == "session":
        parent = get_session(fw, container)
    elif level == "acquistion":
        parent = get_acquisition(fw, container)
    elif level == "analysis":
        parent = get_analysis(fw, container)

    return parent



def get_level(fw, id, level):
    if level == 'project':
        container = fw.get_project(id)
    elif level == 'subject':
        container = fw.get_subject(id)
    elif level == 'session':
        container = fw.get_session(id)
    elif level == 'acquisition':
        container = fw.get_acquisition(id)
    elif level == 'analysis':
        container = fw.get_analysis(id)
    else:
        container = None
    
    return container
    
    

def generate_path_to_container(
        fw,
        container,
        group = None,
        project = None,
        subject = None,
        session = None,
        acquisition = None,
        analysis = None
):
    
    try:
        ct = container.container_type
    except Exception:
        ct = 'analysis'
    
    
    if ct == "file":
        path_to_file = generate_path_to_container(
            fw,
            container.parent.reload(),
            group,
            project,
            subject,
            session,
            acquisition,
            analysis)

        fw_path = f"{path_to_file}/{container.name}"

    else:
        fw_path = ''
        
        if group is not None:
            append = group
        elif group is None and container.parents.group is not None:
            append = container.parents.group
        else:
            append = ''
        
        fw_path += append
        
        if project is not None:
            append = f"/{project}"
        elif project is None and container.parents.project is not None:
            project = get_project(fw, container)
            append = f"/{project.label}"
        else:
            append = ''
        
        fw_path += append
        
        if subject is not None:
            append = f"/{subject}"
        elif subject is None and container.parents.subject is not None:
            subject = get_subject(fw, container)
            append = f"/{subject.label}"
        else:
            append = ''
        
        fw_path += append
        
        if session is not None:
            append = f"/{session}"
        elif session is None and container.parents.session is not None:
            session = get_session(fw, container)
            append = f"/{session.label}"
        else:
            append = ''
        
        fw_path += append
        
        if acquisition is not None:
            append = f"/{acquisition}"
        elif acquisition is None and container.parents.acquisition is not None:
            acquisition = get_acquisition(fw, container)
            append = f"/{acquisition.label}"
        else:
            append = ''

        fw_path += append
        
        if analysis is not None:
            append = f"/{analysis}"
        elif analysis is None and container.get('container_type', 'analysis') == 'analysis':
            analysis = container.label
            append = f"/{analysis}"
        else:
            analysis = ''
        
        fw_path += append
        
        # append = f"/{container.label}"
        # 
        # fw_path += append
        
    return fw_path
