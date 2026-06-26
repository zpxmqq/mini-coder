from retriever import build_tool_index, route

class ToolRegistry:

    def __init__(self, all_tools):
        self.all_tools = all_tools
        self.schemas = {t["function"]["name"]: t for t in all_tools}
        self.index = build_tool_index(self.all_tools)     
    
    def select(self, query, k=3):
        names = route(query, self.index, k)
        return [self.schemas[n] for n in names]
    
if __name__ == "__main__":
    from tool import ALL_TOOLS
    tools = ALL_TOOLS

    registry = ToolRegistry(tools)
    schemas = registry.select("帮我读取文件", k=2)
    for s in schemas:
        print(s["function"]["name"])