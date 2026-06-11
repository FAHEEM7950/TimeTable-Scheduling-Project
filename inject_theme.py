import os

TEMPLATES_DIR = r"d:\TimetableProject\templates"
SCRIPT_TAG = '<script src="{{ url_for(\'static\', filename=\'theme.js\') }}"></script>'

def inject_script_into_templates():
    count = 0
    for filename in os.listdir(TEMPLATES_DIR):
        if filename.endswith(".html"):
            filepath = os.path.join(TEMPLATES_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # If the script is already referenced, skip
            if "theme.js" in content:
                print(f"Skipping {filename} (already has theme.js)")
                continue
            
            # Find the head tag
            if "</head>" in content:
                # Inject before </head>
                new_content = content.replace("</head>", f"    {SCRIPT_TAG}\n</head>")
            elif "<body>" in content:
                new_content = content.replace("<body>", f"<body>\n    {SCRIPT_TAG}")
            else:
                # Fallback to appending at the top of body or top of file
                new_content = f"{SCRIPT_TAG}\n{content}"
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Injected theme.js into {filename}")
            count += 1
            
    print(f"Done! Injected script into {count} templates.")

if __name__ == "__main__":
    inject_script_into_templates()
