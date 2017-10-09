import * as React from 'react';
import './App.css';
import LaundryMachine from './LaundryMachine';
import StatusBar from './StatusBar';

const logo = require('./logo.svg');

// JSON keys as defined by the server
const JSON_URL = 'http://frederick-607.appspot.com/';
const WASHER = 'washer';
const DRYER = 'dryer';
const TIMESTAMP = 'timestamp';
const DRAW = 'draw';

interface AppState {
  attemptedConnection: boolean;

  washerTimestamp?: number;
  washerDraw?: number;

  dryerTimestamp?: number;
  dryerDraw?: number;
}

class App extends React.Component<{}, AppState> {
  timerID: number;

  constructor() {
    super();

    this.state = {attemptedConnection: false,
                  washerTimestamp: undefined,
                  washerDraw: undefined,
                  dryerTimestamp: undefined,
                  dryerDraw: undefined};

    this.fetchDataFromServer();
  }

  render() {
    return (
      <div className="App">

        <div className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h3>607-609 Frederick Laundry</h3>
        </div>
        
        <div className="App-content">
          <LaundryMachine name="Washer" draw={this.state.washerDraw}/>
          <LaundryMachine name="Dryer" draw={this.state.dryerDraw}/>
        </div>
        
        <StatusBar
          attemptedConnection={this.state.attemptedConnection}
          washerTimestamp={this.state.washerTimestamp}
          dryerTimestamp={this.state.dryerTimestamp}
        />
      </div>
    );
  }

  componentDidMount() {
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
        washerTimestamp: Date.now(),
        washerDraw: Math.floor(Math.random() * 500),
        dryerTimestamp: Date.now(),
        dryerDraw: 0
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
              washerDraw: undefined,
              dryerTimestamp: undefined,
              dryerDraw: undefined
          });

          return;
        }
  
        response.json().then(function(data: {}) {
          app.setState({
            attemptedConnection: true,
            washerTimestamp: data[WASHER][TIMESTAMP],
            washerDraw: data[WASHER][DRAW],
            dryerTimestamp: data[DRYER][TIMESTAMP],
            dryerDraw: data[DRYER][DRAW]
          });
        });  
      }  
    )  
    .catch(function(err: Error) {
      app.setState({
        attemptedConnection: true,
        washerTimestamp: undefined,
        washerDraw: undefined,
        dryerTimestamp: undefined,
        dryerDraw: undefined
      });
    });
  }
}

export default App;