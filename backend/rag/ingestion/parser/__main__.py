#--------------------------------------PARSER RUNNER-------------------------------------------

import os
from . import parse


def main():

    test_file = os.path.join("docs", "azure_sql.md")

    print("\n Running parser...\n")

    docs = parse(test_file)

    doc = docs[0]

    print("\n--- TEXT PREVIEW ---\n")
    print(doc.text[:500])

    print("\n--- METADATA ---\n")
    print(doc.metadata.keys())

    print("\n--- AST SAMPLE ---\n")

    for section in doc.metadata["ast"][:2]:
        print(section)
        print("-" * 60)


if __name__ == "__main__":
    main()