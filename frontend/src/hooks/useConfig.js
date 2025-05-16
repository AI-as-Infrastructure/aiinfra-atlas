import { useState, useEffect } from "react";
import axios from "axios";

export const useConfig = (configUrl) => {
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setLoading(true);
        const response = await axios.get(configUrl);
        setConfig(response.data);
      } catch (error) {
        console.error("❌ Error fetching config:", error);
        setError(error);
      } finally {
        setLoading(false);
      }
    };
    fetchConfig();
  }, [configUrl]);

  return { config, loading, error };
};