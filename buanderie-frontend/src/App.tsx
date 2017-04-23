import * as React from 'react';
import './App.css';

const logo = require('./logo.svg');

class App extends React.Component<{}, null> {
  render() {
    return (
      <div className="App">
        <div className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h2>607-609 Frederick</h2>
        </div>
        <p className="App-intro">
          Nothing to see here yet!
        </p>
      </div>
    );
  }
}

export default App;
