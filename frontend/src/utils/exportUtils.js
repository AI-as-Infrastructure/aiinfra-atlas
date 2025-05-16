/**
 * Exports the current chat session as a downloadable JSON file
 * @param {Object} config - The current configuration settings
 * @param {Array} chatHistory - The conversation history
 */
export const exportChatSession = (config, chatHistory) => {
	const date = new Date();
	const dateString = date.toISOString().split("T")[0];
	const timeString = date.toTimeString().split(" ")[0].replace(/:/g, "-");
	const dateTimeString = `${dateString}_${timeString}`;
	
	const data = {
	  date: date.toISOString(),
	  config,
	  chatHistory,
	};
	
	const json = JSON.stringify(data, null, 2);
	const blob = new Blob([json], { type: "application/json" });
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = `ATLAS_${dateTimeString}.json`;
	a.click();
	URL.revokeObjectURL(url);
  };