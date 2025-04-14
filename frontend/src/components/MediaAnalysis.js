import React from 'react';

/**
 * MediaAnalysis Component
 *
 * Displays media sentiment analysis for the stock.
 *
 * Props:
 * - mediaSentiment: The media sentiment text to display.
 * - loading: Boolean flag indicating if the media analysis is still loading.
 */
const MediaAnalysis = ({ mediaSentiment, loading }) => {
  return (
    <div className="card">
      <h2>Media Analysis</h2>
      {loading ? (
        // Show a loading message while the media analysis is being fetched.
        <p>Loading media analysis...</p>
      ) : (
        // Once loaded, display the media sentiment.
        <div className="media-summary">
          <p>{mediaSentiment}</p>
        </div>
      )}
    </div>
  );
};

export default MediaAnalysis;
