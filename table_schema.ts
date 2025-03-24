import { z } from 'zod';

const RowSchema = z.object({
  Date: z.string().describe('Date of the row'),
  Location: z.string().describe('Location of the row'),
  Breakfast_provided: z.boolean().describe('Whether breakfast was provided or not'),
  Lunch_provided: z.boolean().describe('Whether lunch was provided or not'),
  Dinner_provided: z.boolean().describe('Whether dinner was provided or not'),
  Allowance: z.number().describe('The allowance for the row'),
});

const TableSchema = z.object({
  rows: z.array(RowSchema).describe('List of rows in the table'),
});

// Export the schemas
export { RowSchema, TableSchema };
