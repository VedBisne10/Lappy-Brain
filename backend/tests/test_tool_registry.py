from tool_registry import tool_registry

result = tool_registry.execute(
    tool_name="read_file",
    arguments={
        "file_path": r"C:\\Users\\HP\\OneDrive\\Desktop\\All_Folders\\Programming Languages\\Python\\hello.py"
    }
)

print(result)