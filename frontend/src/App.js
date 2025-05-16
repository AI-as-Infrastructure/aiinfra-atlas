import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import AtlasUI from './AtlasUI';
import './index.scss';

function App() {
  return (
    <Router>
      <div className="App">
        <AtlasUI />
      </div>
    </Router>
  );
}

export default App;