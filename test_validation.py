from spdx_tools.spdx3.validation.json_ld.shacl_validation import validate_against_shacl_from_file
import os

def test_validation():
    jsonld_file = "findings/test_spdx3_v2.jsonld.jsonld"
    if not os.path.exists(jsonld_file):
        print(f"File {jsonld_file} not found.")
        return

    print(f"Validating {jsonld_file}...")
    # validate_against_shacl_from_file(json_ld_file, shacl_file)
    # The library might have a default SHACL file or I might need to provide one.
    # Usually it's included in the package.
    
    # Let's try to find where the shacl files are.
    from pyshacl import validate
    from rdflib import Graph
    
    import spdx_tools.spdx3.writer.json_ld as jlw
    shacl_path = os.path.join(os.path.dirname(jlw.__file__), "model.ttl")
    print(f"SHACL path: {shacl_path}")
    
    if os.path.exists(shacl_path):
        data_graph = Graph().parse(jsonld_file, format="json-ld")
        # Explicitly read with utf-8 to avoid Windows locale issues
        with open(shacl_path, "r", encoding="utf-8") as f:
            shacl_graph = Graph().parse(data=f.read(), format="turtle")
            
        print("Starting SHACL validation (this may take a minute)...")
        conforms, results_graph, results_text = validate(data_graph, shacl_graph=shacl_graph)
        print(f"Conforms: {conforms}")
        if not conforms:
            print("Validation Results:")
            print(results_text)
    else:
        print("SHACL file not found.")

if __name__ == "__main__":
    try:
        test_validation()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
