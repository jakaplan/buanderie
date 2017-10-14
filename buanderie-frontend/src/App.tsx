import * as React from 'react';
import './App.css';
import LaundryMachine from './LaundryMachine';
import StatusBar from './StatusBar';

const logo = require('./logo.svg');
const washer = require('./washer.svg');
const dryer = require('./dryer.svg');

// JSON keys as defined by the server
const JSON_URL = 'https://frederick-607.appspot.com/';
const WASHER = 'washer';
const DRYER = 'dryer';
const TIMESTAMP = 'timestamp';
const MILLIWATTS = 'draw';

interface AppState {
  attemptedConnection: boolean;

  washerTimestamp?: number;
  washerMilliwatts?: number;

  dryerTimestamp?: number;
  dryerMilliwatts?: number;
}

class App extends React.Component<{}, AppState> {
  timerID: number;

  constructor() {
    super();

    this.state = {attemptedConnection: false,
                  washerTimestamp: undefined,
                  washerMilliwatts: undefined,
                  dryerTimestamp: undefined,
                  dryerMilliwatts: undefined};
  }

  render() {
    return (
      <div className="App">

        <div className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h3>607-609 Frederick Laundry</h3>
        </div>
        
        <div className="App-content">
          <LaundryMachine
            name="Washer"
            image={washer}
            milliwatts={this.state.washerMilliwatts}
            timestamp={this.state.washerTimestamp}
          />
          <LaundryMachine
            name="Dryer"
            image={dryer}
            milliwatts={this.state.dryerMilliwatts}
            timestamp={this.state.dryerTimestamp}
          />
        </div>
        
        <footer>
          <StatusBar
            attemptedConnection={this.state.attemptedConnection}
            washerTimestamp={this.state.washerTimestamp}
            dryerTimestamp={this.state.dryerTimestamp}
          />
        </footer>
      </div>
    );
  }

  componentDidMount() {
    this.fetchDataFromServer();

    this.timerID = window.setInterval(
        () => this.fetchDataFromServer(),
        5000
    );
  }
    
  componentWillUnmount() {
      window.clearInterval(this.timerID);
  }

  // Test function instead of talking to server
  simulateFetchDataFromServer() {
      this.setState({
        attemptedConnection: true,
        washerTimestamp: (Date.now() - 12000),
        washerMilliwatts: Math.floor(Math.random() * 500),
        dryerTimestamp: (Date.now() - 1210),
        dryerMilliwatts: 0
      });
  }

  fetchDataFromServer() {
    let app = this;

    fetch(JSON_URL)  
    .then(  
      function(response: Response) {
        if (response.status !== 200) {  
          app.setState({
              attemptedConnection: true,
              washerTimestamp: undefined,
              washerMilliwatts: undefined,
              dryerTimestamp: undefined,
              dryerMilliwatts: undefined
          });

          return;
        }
  
        response.json().then(function(data: {}) {
          app.setState({
            attemptedConnection: true,
            washerTimestamp: data[WASHER][TIMESTAMP],
            washerMilliwatts: data[WASHER][MILLIWATTS],
            dryerTimestamp: data[DRYER][TIMESTAMP],
            dryerMilliwatts: data[DRYER][MILLIWATTS]
          });
        });  
      }  
    )  
    .catch(function(err: Error) {
      app.setState({
        attemptedConnection: true,
        washerTimestamp: undefined,
        washerMilliwatts: undefined,
        dryerTimestamp: undefined,
        dryerMilliwatts: undefined
      });
    });
  }
}

export default App;