import os
from django.core.management.base import BaseCommand
from apps.code_scan.models import ScanProject
from apps.code_scan.services import ScanService
from core.user.user_model import User

class MockFile:
    def __init__(self, name, content):
        self.name = name
        self.content = content.encode('utf-8')

    def read(self):
        return self.content

class Command(BaseCommand):
    help = 'Mock CppCheck scan data for a project'

    def handle(self, *args, **options):
        self.stdout.write("Starting to mock CppCheck data...")

        # 1. Get All Projects
        projects = ScanProject.objects.filter(is_deleted=False)
        if not projects.exists():
            user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR("No users found to assign as creator."))
                return
            
            project = ScanProject.objects.create(
                name="Mock CppCheck Project",
                repo_url="https://github.com/example/cpp-project",
                branch="main",
                description="A mock project for testing CppCheck integration",
                sys_creator=user
            )
            projects = [project]
            self.stdout.write(f"Created new project: {project.name}")
        
        # 2. Generate Mock XML Data
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<results version="2">
    <cppcheck version="2.10"/>
    <errors>
        <error id="memleak" severity="error" msg="Memory leak: p" verbose="Memory leak: p" cwe="401" file="src/main.cpp" line="42" column="10">
            <location file="src/main.cpp" line="42" column="10"/>
        </error>
        <error id="arrayIndexOutOfBounds" severity="error" msg="Array 'a[10]' accessed at index 10, which is out of bounds." verbose="Array 'a[10]' accessed at index 10, which is out of bounds." cwe="119" file="src/utils.cpp" line="15" column="5">
             <location file="src/utils.cpp" line="15" column="5"/>
        </error>
        <error id="unreadVariable" severity="style" msg="Variable 'x' is assigned a value that is never used." verbose="Variable 'x' is assigned a value that is never used." cwe="563" file="src/test.cpp" line="8" column="9">
            <location file="src/test.cpp" line="8" column="9"/>
        </error>
        <error id="nullPointer" severity="error" msg="Null pointer dereference: ptr" verbose="Null pointer dereference: ptr" cwe="476" file="src/core/engine.cpp" line="102" column="15">
            <location file="src/core/engine.cpp" line="102" column="15"/>
        </error>
    </errors>
</results>
"""
        
        mock_file = MockFile("mock_cppcheck_report.xml", xml_content)

        # 3. Upload and Process for EACH project
        for project in projects:
            self.stdout.write(f"Processing project: {project.name} ({project.id})")
            try:
                task = ScanService.handle_upload(
                    project_key=str(project.project_key),
                    tool_name="cppcheck",
                    file_obj=mock_file
                )
                self.stdout.write(self.style.SUCCESS(f"Successfully created ScanTask {task.id} for project {project.name}"))
                
                # Refresh task to get updated status
                task.refresh_from_db()
                
                if task.status == 'success':
                    self.stdout.write(self.style.SUCCESS(f"Task processed successfully. Log: {task.log}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Task status: {task.status}. Log: {task.log}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to mock data for project {project.name}: {str(e)}"))
