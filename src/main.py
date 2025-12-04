

from cProfile import Profile
from pstats import SortKey, Stats


from application.managers.project_managers.cross_sectionnal_project.cross_sectionnal_project_manager import CrossSectionnal
from application.managers.project_managers.test_base_project.test_base_project_manager import TestBaseProjectManager






if __name__ == '__main__':
    #TestBaseProjectManager().web_interface.start_interface_and_open_browser()
    #TestBaseProjectManager().run()
    CrossSectionnal().run()
    
   


    