import inspect
from pathlib import Path
import mkdocs_gen_files
import pkgutil

# Specify your package's top-level directory
src = Path("my_package")
api_dir = Path("api")

def generate_doc_page(obj_name, path_prefix):
    """Generates a Markdown file for a given object."""
    doc_path = (path_prefix / f"{obj_name}.md").as_posix()
    with mkdocs_gen_files.open(doc_path, "w") as fd:
        print(f"::: {path_prefix.as_posix().replace('/', '.')}.{obj_name}", file=fd)

def inspect_and_document(module_name, module_path):
    """Inspects a module and generates pages for its contents."""
    module = __import__(module_name, fromlist=[""])
    
    # Create a page for the module itself
    module_path_for_doc = api_dir / module_path
    with mkdocs_gen_files.open(f"{module_path_for_doc}.md", "w") as fd:
        print(f"::: {module_name}", file=fd)

    # Inspect the module for classes and methods
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
            # Create a page for the class
            class_path = module_path_for_doc / name
            generate_doc_page(name, module_path_for_doc)
            
            # Create sub-pages for each method in the class
            for m_name, m_obj in inspect.getmembers(obj):
                if inspect.isfunction(m_obj):
                    method_path = class_path / m_name
                    generate_doc_page(m_name, class_path)

# Walk the package to find all modules
for loader, module_name, is_pkg in pkgutil.walk_packages([src.parent]):
    if module_name.startswith("my_package"):
        module_path = Path(module_name.replace('.', '/'))
        inspect_and_document(module_name, module_path)
