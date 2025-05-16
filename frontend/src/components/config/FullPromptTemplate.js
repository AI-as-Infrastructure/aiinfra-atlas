/**
 * HTML template for displaying the full system prompt in a new tab.
 * This template is designed to match the style of the citation view.
 * 
 * @param {string} promptText - The full system prompt text to display
 * @returns {string} HTML content for the new tab
 */
const createFullPromptHtml = (promptText) => {
	return `
	  <!DOCTYPE html>
	  <html lang="en">
	  <head>
		<meta charset="UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<title>ATLAS System Prompt</title>
		<style>
		  body {
			font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
			line-height: 1.6;
			padding: 20px;
			max-width: 800px;
			margin: 0 auto;
			color: #333;
			font-size: 12px;
			background-color: #F5F5F5;
		  }
		  h2 {
			color: #000;
			border-bottom: 1px solid #eee;
			padding-bottom: 10px;
			margin-bottom: 20px;
			font-size: 1.4rem;
		  }
		  .prompt-container {
			background-color: #fff;
			border: 1px solid #e1e4e8;
			border-radius: 6px;
			padding: 15px;
			white-space: pre-wrap;
			font-family: monospace;
			overflow-x: auto;
			font-size: 12px;
			line-height: 1.5;
			margin-bottom: 20px;
			box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
		  }
		  .back-link {
			color: #000;
			text-decoration: underline;
			font-size: 12px;
			display: inline-block;
			margin-top: 10px;
		  }
		  .back-link:hover {
			color: #888;
		  }
		</style>
	  </head>
	  <body>
		<h2>ATLAS System Prompt</h2>
		<div class="prompt-container">${promptText}</div>
		<a href="javascript:window.close()" class="back-link">Close this page</a>
	  </body>
	  </html>
	`;
  };
  
  export default createFullPromptHtml;