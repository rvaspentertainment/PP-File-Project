from aiohttp import web

async def web_server():
    """Create a simple web server for health checks"""
    routes = web.RouteTableDef()
    
    @routes.get("/", allow_head=True)
    async def root_route_handler(request):
        return web.json_response({
            "status": "running",
            "message": "Bot is alive!"
        })
    
    @routes.get("/health")
    async def health_check(request):
        return web.json_response({
            "status": "healthy"
        })
    
    app = web.Application()
    app.add_routes(routes)
    return app
