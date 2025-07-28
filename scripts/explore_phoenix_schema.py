#!/usr/bin/env python3
"""
Script to explore your Phoenix GraphQL schema and see what data is available.
Run this to understand your Phoenix setup before customizing the inter-rater query.
"""

import os
import json
import httpx
import asyncio
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

# Find the project root and load environment
project_root = Path(__file__).parent.parent
env_file = project_root / "config" / f".env.{os.getenv('ENVIRONMENT', 'development')}"

if env_file.exists():
    load_dotenv(env_file)
    print(f"Loaded environment from: {env_file}")
else:
    print(f"Environment file not found: {env_file}")

async def explore_phoenix_schema():
    """Explore Phoenix GraphQL schema and available data."""
    
    # Get Phoenix configuration
    phoenix_base_url = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006")
    phoenix_api_key = os.getenv("PHOENIX_API_KEY")
    phoenix_client_headers = os.getenv("PHOENIX_CLIENT_HEADERS")
    
    if phoenix_base_url.endswith('/v1/traces'):
        phoenix_base_url = phoenix_base_url[:-10]
    
    print(f"Phoenix Base URL: {phoenix_base_url}")
    print(f"API Key configured: {'Yes' if phoenix_api_key else 'No'}")
    print(f"Client Headers configured: {'Yes' if phoenix_client_headers else 'No'}")
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    if phoenix_api_key:
        api_key = phoenix_api_key.replace('api_key=', '') if phoenix_api_key.startswith('api_key=') else phoenix_api_key
        headers['api_key'] = api_key
    
    print(f"Headers: {headers}")
    
    # GraphQL endpoint
    graphql_endpoint = f"{phoenix_base_url}/graphql"
    print(f"GraphQL Endpoint: {graphql_endpoint}")
    
    # 1. Get schema introspection
    introspection_query = """
    query IntrospectionQuery {
      __schema {
        queryType { name }
        mutationType { name }
        subscriptionType { name }
        types {
          ...FullType
        }
      }
    }
    
    fragment FullType on __Type {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        description
        type {
          ...TypeRef
        }
      }
    }
    
    fragment TypeRef on __Type {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
        }
      }
    }
    """
    
    try:
        async with httpx.AsyncClient() as client:
            print("\n1. Testing Phoenix connection...")
            response = await client.post(
                graphql_endpoint,
                json={"query": "{ __typename }"},
                headers=headers,
                timeout=10.0
            )
            
            print(f"Connection test status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error: {response.text}")
                return
            
            print("✅ Phoenix connection successful!")
            
            # 2. Get sample projects
            print("\n2. Getting available projects...")
            projects_query = """
            query GetProjects {
              projects {
                name
                description
                startTime
                endTime
              }
            }
            """
            
            response = await client.post(
                graphql_endpoint,
                json={"query": projects_query},
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if "errors" not in data:
                    projects = data.get("data", {}).get("projects", [])
                    print(f"Found {len(projects)} projects:")
                    for project in projects[:5]:  # Show first 5
                        print(f"  - {project.get('name', 'Unknown')}")
                else:
                    print(f"GraphQL errors: {data['errors']}")
            
            # 3. Get sample spans from your project
            print("\n3. Getting sample spans...")
            project_name = os.getenv("INTER_RATER_PROJECT", "atlas-hansard")
            
            spans_query = """
            query GetSampleSpans($projectName: String!) {
              spans(
                filter: { projectName: $projectName }
                first: 3
                sort: { startTime: DESC }
              ) {
                edges {
                  node {
                    spanId
                    name
                    startTime
                    attributes
                    annotations {
                      name
                      annotatorKind
                      result {
                        __typename
                        ... on ScoreResult {
                          score
                        }
                        ... on TextResult {
                          text
                        }
                        ... on CategoricalResult {
                          category
                        }
                      }
                      metadata
                    }
                  }
                }
              }
            }
            """
            
            response = await client.post(
                graphql_endpoint,
                json={
                    "query": spans_query,
                    "variables": {"projectName": project_name}
                },
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if "errors" not in data:
                    spans = data.get("data", {}).get("spans", {}).get("edges", [])
                    print(f"Found {len(spans)} sample spans in project '{project_name}':")
                    
                    for i, edge in enumerate(spans):
                        span = edge.get("node", {})
                        print(f"\n  Span {i+1}:")
                        print(f"    ID: {span.get('spanId', 'Unknown')}")
                        print(f"    Name: {span.get('name', 'Unknown')}")
                        print(f"    Start Time: {span.get('startTime', 'Unknown')}")
                        
                        # Show attributes
                        attributes = span.get("attributes", {})
                        print(f"    Attributes ({len(attributes)}):")
                        for key, value in list(attributes.items())[:5]:  # First 5 attributes
                            print(f"      {key}: {str(value)[:100]}...")
                        
                        # Show annotations (feedback)
                        annotations = span.get("annotations", [])
                        print(f"    Annotations/Feedback ({len(annotations)}):")
                        for annotation in annotations:
                            name = annotation.get("name", "Unknown")
                            result = annotation.get("result", {})
                            print(f"      {name}: {result}")
                
                else:
                    print(f"GraphQL errors: {data['errors']}")
            else:
                print(f"Spans query failed: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"Error exploring Phoenix: {e}")

if __name__ == "__main__":
    asyncio.run(explore_phoenix_schema())
