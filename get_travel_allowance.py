import os
import sys
import asyncio
import base64
import json
from pathlib import Path
from playwright.async_api import async_playwright
from openai import OpenAI
from typing import Dict, Any, List
from pydantic import Field, BaseModel

class Row(BaseModel):
    Date: str = Field(..., description = 'Date of the row')
    Location: str = Field(..., description = 'Location of the row')
    Breakfast_provided: bool = Field(..., description = 'Whether breakfast was provided or not')
    Lunch_provided: bool = Field(..., description = 'Whether lunch was provided or not')
    Dinner_provided: bool = Field(..., description = 'Whether dinner was provided or not')
    Allowance: float = Field(..., description = 'The allowance for the row')

class Table(BaseModel):
    rows: List[Row] = Field(..., description = 'List of rows in the table')

class TravelAllowanceFetcher:
    def __init__(self, openai_client = None):
        """
        Initialize the TravelAllowanceFetcher with an OpenAI client.
        
        Args:
            openai_client: An initialized OpenAI client
        """
        self.openai_client = openai_client
        self.storage_state_path = os.path.join(os.path.dirname(__file__), "storage_state.json")
    
    async def fetch_travel_allowance(self, user_id = None, report_id = None):
        """
        Fetch travel allowance data using Playwright to navigate through Concur
        and OpenAI's vision capabilities to extract table data.
        
        Args:
            user_id: User ID for Concur
            report_id: Report ID for Concur
            
        Returns:
            Table: A Table object containing the travel allowance data
        """
        async with async_playwright() as p:
            # Launch browser
            browser = await p.firefox.launch(headless=False)
            
            try:
                # Check if storage state exists (for authentication)
                if Path(self.storage_state_path).exists():
                    context = await browser.new_context(storage_state=self.storage_state_path)
                else:
                    # If no storage state, create a new context
                    context = await browser.new_context()
                
                # Print status messages along the way
                page = await context.new_page()
                # breakpoint()
                await page.goto('https://concur.cornell.edu');
                await page.wait_for_selector('text=Available Expenses', timeout=60000)
                await page.goto('https://us2.concursolutions.com/nui/expense#available-expenses');
                await page.click('text=Active Reports')
                await page.click('text=This Year')
                await page.click('text=Kickoff of AII Lab Spring CohortNo: G6T88Z / ID: 6B3FFE88DC74445E8C82')
                await page.click('button:has-text("Travel Allowance")')
                await page.get_by_role('menuitem', name='View Travel Allowance').click()
                await page.click('text=Expenses & Adjustments')
                await page.wait_for_selector('text=Exclude | All', timeout=60000)
                
               
                # Take a screenshot of the page
                screenshot_path = 'travel_allowance_screenshot.png'
                await page.screenshot(path=screenshot_path)
                
                # Extract table data using OpenAI's vision capabilities
                table_data = await self._extract_table_from_screenshot(screenshot_path)
                
                return table_data
                
            finally:
                await browser.close()
    
    def _create_json_schema(self):
        """
        Create a JSON schema for the Table model.
        
        Returns:
            Dict: A JSON schema for the Table model
        """
        return {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "description": "List of rows in the table",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Date": {
                                "type": "string",
                                "description": "Date of the row"
                            },
                            "Location": {
                                "type": "string",
                                "description": "Location of the row"
                            },
                            "Breakfast_provided": {
                                "type": "boolean",
                                "description": "Whether breakfast was provided or not"
                            },
                            "Lunch_provided": {
                                "type": "boolean",
                                "description": "Whether lunch was provided or not"
                            },
                            "Dinner_provided": {
                                "type": "boolean",
                                "description": "Whether dinner was provided or not"
                            },
                            "Allowance": {
                                "type": "number",
                                "description": "The allowance for the row"
                            }
                        },
                        "required": ["Date", "Location", "Breakfast_provided", "Lunch_provided", "Dinner_provided", "Allowance"]
                    }
                }
            },
            "required": ["rows"]
        }
    
    async def _extract_table_from_screenshot(self, screenshot_path):
        """
        Extract table data from a screenshot using OpenAI's vision capabilities.
        
        Args:
            screenshot_path: Path to the screenshot file
            
        Returns:
            Table: A Table object containing the extracted table data
        """
        # Read the screenshot file
        with open(screenshot_path, "rb") as image_file:
            screenshot_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Prepare the prompt for OpenAI
        prompt = "Extract the travel allowance table from this screenshot. Return the data as a structured table with columns for Date, Location, whether Breakfast/Lunch/Dinner was provided, and Allowance amount."
        
        # Create the JSON schema for the response
        json_schema = self._create_json_schema()
        
        # Call OpenAI API with the screenshot and schema
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that processes visual data."},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"}}
                    ]}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            response_content = response.choices[0].message.content
            table_data = json.loads(response_content)
            
            # Convert to Table object
            rows = []
            for row_data in table_data.get('rows', []):
                row = Row(
                    Date=row_data.get('Date', ''),
                    Location=row_data.get('Location', ''),
                    Breakfast_provided=row_data.get('Breakfast_provided', False),
                    Lunch_provided=row_data.get('Lunch_provided', False),
                    Dinner_provided=row_data.get('Dinner_provided', False),
                    Allowance=float(row_data.get('Allowance', 0.0))
                )
                rows.append(row)
            
            return Table(rows=rows)
            
        except Exception as e:
            print(f"Error extracting table data: {e}")
            # Fallback to text parsing if JSON parsing fails
            return await self._extract_table_from_screenshot_text_fallback(screenshot_path)
    
    async def _extract_table_from_screenshot_text_fallback(self, screenshot_path):
        """
        Fallback method to extract table data from a screenshot using text parsing.
        
        Args:
            screenshot_path: Path to the screenshot file
            
        Returns:
            Table: A Table object containing the extracted table data
        """
        # Read the screenshot file
        with open(screenshot_path, "rb") as image_file:
            screenshot_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Call OpenAI API with the screenshot
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that processes visual data."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Extract the travel allowance table from this screenshot. Format it as a markdown table with columns for Date, Location, Breakfast Provided, Lunch Provided, Dinner Provided, and Allowance amount."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"}}
                ]}
            ]
        )
        
        # Process the response to extract table data
        table_text = response.choices[0].message.content
        
        # Parse the table text into a structured format
        rows = []
        
        # This is a simplified parsing logic - you might need to adjust based on the actual response format
        lines = table_text.strip().split('\n')
        for line in lines:
            if '|' in line and not line.startswith('|---') and not line.startswith('| Date'):
                cells = [cell.strip() for cell in line.split('|')]
                if len(cells) >= 6:  # Ensure we have enough cells
                    date = cells[1]
                    location = cells[2]
                    breakfast = 'Yes' in cells[3] or 'yes' in cells[3] or 'true' in cells[3].lower()
                    lunch = 'Yes' in cells[4] or 'yes' in cells[4] or 'true' in cells[4].lower()
                    dinner = 'Yes' in cells[5] or 'yes' in cells[5] or 'true' in cells[5].lower()
                    allowance = float(cells[6].replace('$', '').replace(',', '')) if len(cells) > 6 else 0.0
                    
                    row = Row(
                        Date=date,
                        Location=location,
                        Breakfast_provided=breakfast,
                        Lunch_provided=lunch,
                        Dinner_provided=dinner,
                        Allowance=allowance
                    )
                    rows.append(row)
        
        return Table(rows=rows)


asyncio.run(TravelAllowanceFetcher().fetch_travel_allowance())