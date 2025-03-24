import { test, expect } from '@playwright/test';
import fs from 'fs';
import OpenAI from 'openai';
import { zodToJsonSchema } from 'zod-to-json-schema';
// import zodResponseFormat from "zod-to-json-schema";
import { TableSchema } from '../table_schema'
import { z } from 'zod';

// Require the dotenv package
require('dotenv').config();

const openai = new OpenAI({
    apiKey: process.env.API_KEY, // Replace with your OpenAI API key
	baseURL: process.env.BASE_URL
});

function zodResponseFormat(schema: z.ZodTypeAny, description: string) {
    return {
        type: 'json_schema' as const, // Explicitly define as a literal type
        json_schema: {
            name: 'TravelAllowancesTable',
            description: description,
            schema: zodToJsonSchema(schema),
            strict: true
        }
    };
}

// Load storage state from storage_state.json
test.use({
    storageState: 'storage_state.json',
});

// Test script
test('extract data from second table using locator', async ({ page }) => {
	test.setTimeout(600000)
    // Navigate through the app
    await page.goto('https://concur.cornell.edu');
    await expect(page.getByText('Available Expenses').first()).toBeVisible({ timeout: 60000 });
    await page.goto('https://us2.concursolutions.com/nui/expense#available-expenses');
    await page.getByText('Active Reports').click();
    await page.getByText('Last 90 Days').click();
    await page.getByText('Kickoff of AII Lab Spring CohortNo: G6T88Z / ID: 6B3FFE88DC74445E8C82').click();
    await page.getByRole('button', { name: 'Travel Allowance' }).click();
    await page.getByRole('menuitem', { name: 'View Travel Allowance' }).click();
    await page.getByText('Expenses & Adjustments').click();
	await expect(page.getByText('Exclude | All').first()).toBeVisible({ timeout: 60000 });

    // Take a screenshot of the current page
    const screenshotPath = 'screenshot.png';
    await page.screenshot({ path: screenshotPath });

    console.log("Screenshot captured...");

    // Convert the screenshot to base64 format
    const screenshotBuffer = fs.readFileSync(screenshotPath);
    const screenshotBase64 = screenshotBuffer.toString('base64');

    // Prompt the LLM using the screenshot data
    const prompt = `
		Extract table from the screenshot.
	`;
	
    // Send the prompt with the screenshot to the OpenAI API
    try {
        const response = await openai.beta.chat.completions.parse({
            model: 'openai.gpt-4o', // Replace with the appropriate model (e.g., gpt-3.5-turbo, gpt-4)
            messages: [
                { role: 'system', content: 'You are a helpful assistant that processes visual data.' },
                { role: 'user', content: [{
					type: 'text',
					text:prompt
				},
				{
                    type: "image_url",
                    image_url: {url: `data:image/png;base64,${screenshotBase64}`},
                }]
			 },
            ],
			response_format: zodResponseFormat(TableSchema, "Travel Allowances Table")
        });

        // Parse and validate the response using Zod
		const tableData = response.choices[0].message

		// If the model refuses to respond, you will get a refusal message
		if (tableData.refusal) {
			console.log(tableData.refusal);
		} else {
			console.log(tableData.parsed);
		}
    } catch (error) {
        console.error('Error:', error);
    }
});