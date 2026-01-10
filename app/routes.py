"""
Project Name: WDW-Transit-Optimizer
File Name: app/routes.py
Description: Routes for the WDW Transit Optimizer application.
Author: Joseph Lefkovitz (github.com/lefkovitzj)
Last Modified: 1/10/2026
"""

# Python standard library imports
from typing import List

# Third-party imports
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_graph(request: Request):
    return request.app.state.graph

@router.get("/", response_class=templates.HTMLResponse)
async def home(request: Request):
    """ Home page route."""
    return templates.TemplateResponse("home.html", {
        "request": request,
        "app_name": request.app.state.config.app_name
    })

@router.post("/search-locations", response_class=HTMLResponse)
async def search(request: Request, q: str = Form(""), graph=Depends(get_graph)):
    """ HTMX Endpoint: Search for locations matching the query. """
    matches = {
        name: loc_id for name, loc_id in graph.display_names.items()
        if q.lower() in name.lower() and loc_id.endswith("_MAIN")
    }
    return templates.TemplateResponse("search_results.html", {
        "request": request,
        "query": q,
        "matches": matches
    })

@router.post("/plan", response_class=HTMLResponse)
async def plan_trip(
    request: Request,
    start: str = Form(...),
    end: str = Form(...),
    stops: List[str] = Form(default=[]),
    graph=Depends(get_graph)
):
    """ Calculate and return the optimized itinerary. """
    result = graph.plan_itinerary(start, end, stops)
    return templates.TemplateResponse("itinerary.html", {
        "request": request,
        "itinerary": result["itinerary"],
        "total_time": result["total_time"],
        "optimized_order": result["optimized_order"]
    })
