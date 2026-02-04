from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from . import db
from .models import DiagramCache
from .services.github_service import GitHubService
from .services.llm_service import LLMService
from app.utils.prompts import (
    SYSTEM_DIAGRAM_PROMPT,
    SYSTEM_CLASS_DIAGRAM_PROMPT,
    SYSTEM_STATE_DIAGRAM_PROMPT,
    SYSTEM_C4_DIAGRAM_PROMPT
)
import re

main = Blueprint('main', __name__)
llm_service = LLMService()

import logging

logger = logging.getLogger(__name__)

@main.route('/')
def index():
    logger.info("Serving index page")
    return render_template('index.html')

@main.route('/generate', methods=['POST'])
def generate():
    data = request.json
    repo_url = data.get('repo_url')
    # Allow user to pass a PAT specifically for this request
    pat = data.get('pat') 
    force_refresh = data.get('force_refresh', False)
    diagram_type = data.get('diagram_type', 'flowchart')
    
    logger.info(f"Received generation request for: {repo_url}, type: {diagram_type}")
    
    if not repo_url:
        logger.warning("Repo URL missing in request")
        return jsonify({"error": "Repo URL is required"}), 400

    # Normalize repo_url to "username/repo"
    try:
        if "github.com/" in repo_url:
            parts = repo_url.split("github.com/")[-1].split("/")
            username = parts[0]
            repo = parts[1].replace(".git", "")
        else:
            parts = repo_url.split("/")
            username = parts[0]
            repo = parts[1]
        logger.debug(f"Normalized repo: {username}/{repo}")
    except Exception as e:
        logger.error(f"Failed to parse repo URL: {repo_url} - {e}")
        return jsonify({"error": "Invalid repository format. Use 'username/repo' or full URL."}), 400

    canonical_key = f"{username}/{repo}".lower()

    # Check Cache
    cached = DiagramCache.query.filter_by(repo_url=canonical_key, diagram_type=diagram_type).first()
    if cached and not force_refresh:
        logger.info(f"Cache HIT for {canonical_key} ({diagram_type})")
        return jsonify({"diagram": cached.diagram_content, "cached": True})
    
    if force_refresh:
        logger.info(f"Force refresh requested for {canonical_key} ({diagram_type})")
    else:
        logger.info(f"Cache MISS for {canonical_key} ({diagram_type})")

    try:
        # Initialize GitHub Service (with optional custom PAT)
        gh_service = GitHubService(pat=pat)
        
        # 1. Fetch Data
        file_tree, default_branch = gh_service.get_file_tree(username, repo)
        readme = gh_service.get_readme(username, repo)
        
        if not file_tree:
            logger.warning(f"File tree empty for {canonical_key}")
            return jsonify({"error": "Could not fetch file tree. Is the repo empty or private?"}), 404

        # 2. Prepare LLM Prompt
        # Construct base URL for links: https://github.com/user/repo/blob/branch/
        base_url = f"https://github.com/{username}/{repo}/blob/{default_branch}/"
        
        repo_context = f"""<CONTEXT>
Repo: {username}/{repo}
Branch: {default_branch}
Base URL: {base_url}
</CONTEXT>

<FILE_TREE>
{file_tree}
</FILE_TREE>

<README>
{readme}
</README>"""
        
        # 3. Call LLM
        # Select prompt based on type
        if diagram_type == 'class':
            system_prompt = SYSTEM_CLASS_DIAGRAM_PROMPT
        elif diagram_type == 'state':
            system_prompt = SYSTEM_STATE_DIAGRAM_PROMPT
        elif diagram_type == 'c4':
            system_prompt = SYSTEM_C4_DIAGRAM_PROMPT
        else:
            system_prompt = SYSTEM_DIAGRAM_PROMPT
            
        repo_context += f"\nIMPORTANT: Generate a {diagram_type} diagram."

        raw_llm_output = llm_service.generate_diagram(
            system_prompt=system_prompt,
            user_content=repo_context
        )
        
        # 4. Clean up Mermaid Code
        cleaned_diagram = clean_mermaid_code(raw_llm_output, diagram_type)
        
        # 5. Cache Result (Only if valid diagram)
        if "Error generating diagram" in cleaned_diagram or "Connection error" in cleaned_diagram:
             logger.warning(f"Generated content contains error, NOT caching: {cleaned_diagram[:50]}...")
        else:
            if cached:
                cached.diagram_content = cleaned_diagram
                cached.created_at = datetime.utcnow()
                logger.info("Updated cache entry")
            else:
                new_entry = DiagramCache(
                    repo_url=canonical_key, 
                    diagram_type=diagram_type,
                    diagram_content=cleaned_diagram
                )
                db.session.add(new_entry)
                logger.info("Created new cache entry")
            
            db.session.commit()
        
        logger.info("Generation successful")
        logger.info(f"FINAL diagram being returned (first 300 chars): {cleaned_diagram[:300]}")
        return jsonify({"diagram": cleaned_diagram, "cached": False})

    except ValueError as e:
        logger.warning(f"ValueError: {e}")
        return jsonify({"error": str(e)}), 404 # Repo not found
    except Exception as e:
        logger.error(f"Server Error processing {canonical_key}: {e}", exc_info=True)
        print(f"Server Error: {e}")
        return jsonify({"error": f"Internal Error: {str(e)}"}), 500

from app.utils.mermaid_utils import clean_mermaid_code

