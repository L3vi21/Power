import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:3000';

function MetricSelector({ onMetricChange }) {
    const [metrics, setMetrics] = useState([]);
    const [selectedMetric, setSelectedMetric] = useState('');

    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/metrics`);
                setMetrics(response.data);
            } catch (error) {
                console.error('Error fetching metrics:', error);
                console.error(error);
            }
        };
        fetchMetrics();
    }, []);

    const handleChange = (event) => {
        const metric = event.target.value;
        setSelectedMetric(metric);
        onMetricChange(metric);
    };

    return (
        <div>
            <label htmlFor="metric-select">Select Metric: </label>
            <select id="metric-select" value={selectedMetric} onChange={handleChange}>
                <option value="">--Select a metric--</option>
                {metrics.map((metric) => (
                    <option key={metric} value={metric}>{metric}</option>
                ))}
            </select>
        </div>
    );
}