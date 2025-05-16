/**
 * HTML template for displaying all citations in a new tab.
 * 
 * @param {Array} citations - The array of citation objects to display
 * @returns {string} HTML content for the new tab
 */
const createCitationsHtml = (citations) => {
	return `
	  <!DOCTYPE html>
	  <html lang="en">
	  <head>
		<meta charset="UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<title>ATLAS Citations</title>
		<style>
		  body {
			font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
			line-height: 1.6;
			padding: 20px;
			max-width: 800px;
			margin: 0 auto;
			color: #333;
			background-color: #F5F5F5;
		  }
		  h2 {
			color: #000;
			border-bottom: 1px solid #eee;
			padding-bottom: 10px;
			margin-bottom: 20px;
		  }
		  .citations-container {
			max-width: 800px;
			margin: 0 auto;
		  }
		  .citation { 
			background-color: #ffffff;
			border: 1px solid #e0e0e0; 
			padding: 15px; 
			margin-bottom: 15px; 
			border-radius: 5px;
			box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		  }
		  h3 { 
			font-size: 14px; 
			margin-top: 0;
			color: #333;
		  }
		  p { 
			margin: 8px 0; 
			font-size: 12px;
			line-height: 1.4;
		  }
		  a { color: #007bff; }
		  .metadata {
			margin-bottom: 10px;
			padding-bottom: 10px;
			border-bottom: 1px solid #eee;
		  }
		  .content {
			white-space: pre-wrap;
			font-size: 12px;
			line-height: 1.5;
			max-height: 300px;
			overflow-y: auto;
			padding: 10px;
			background-color: #f9f9f9;
			border-radius: 4px;
		  }
		  .back-link {
			display: inline-block;
			margin-top: 20px;
			color: #000;
			text-decoration: underline;
			font-size: 12px;
			cursor: pointer;
		  }
		  .back-link:hover {
			color: #666;
		  }
		</style>
	  </head>
	  <body>
		<h2>All Citations (${citations.length})</h2>
		${citations.map((source, i) => `
		  <div class="citation">
			<h3>${source.title || `Citation ${i+1}`}</h3>
			<div class="metadata">
			  <p><strong>Date:</strong> ${source.date || "N/A"}</p>
			  <p><strong>ID:</strong> ${source.id || source.source_id || "N/A"}</p>
			  <p><strong>Corpus:</strong> ${source.corpus || "N/A"}</p>
			  ${source.url ? `<p><strong>Source:</strong> <a href="${source.url}" target="_blank">${source.url}</a></p>` : ''}
			</div>
			<div class="content">
			  ${source.full_content || source.content || source.quote || "No content available"}
			</div>
		  </div>
		`).join('')}
		<a href="javascript:window.close()" class="back-link">Close this page</a>
	  </body>
	  </html>
	`;
  };
  
  export default createCitationsHtml;