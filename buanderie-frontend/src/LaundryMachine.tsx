import * as React from 'react';
import './LaundryMachine.css';

export interface LaundryMachineProps {
    name: string;
    image: string;
    draw?: number; // This is in milliwatts
    timestamp?: number;
}

class LaundryMachine extends React.Component<LaundryMachineProps, {}> {

    constructor(props: LaundryMachineProps) {
        super(props, {});
    }
    
    render() {
        // Status based on recency of data and wattage
        let displayStatus: string;
        let cssStatus: string;

        // If timestamp is more than 60 seconds old
        if (this.props.timestamp && (Date.now() - this.props.timestamp > 60000)) {
            cssStatus = 'draw_unknown';
            displayStatus = 'Data out of date';
        } else { // Otherwise, use draw information
            if (this.props.draw === undefined) {
                cssStatus = 'draw_unknown';
                displayStatus = 'Fetching status...';
            } else if (this.props.draw === 0) {
                cssStatus = 'no_draw';
                displayStatus = 'Available';
            } else {
                cssStatus = 'draw';

                // Display wattage to the nearest tenth of a watt and always show a decimal point
                let roundedWattage = Math.round(this.props.draw / 100) / 10;
                let wattageDisplay = roundedWattage + '';
                if (!wattageDisplay.includes('.')) {
                    wattageDisplay += '.0';
                }
                wattageDisplay += 'W';

                displayStatus = 'Running (' + wattageDisplay + ')';
            }
        }

        // Use the css status as the class name to change the background color via CSS
        let rootClassName: string = 'Laundry-machine ' + cssStatus;

        return (
            <div className={rootClassName}>
                <div className="Machine-name">
                    {this.props.name}
                </div>
                <img src={this.props.image} height={150}/>
                <div className="Machine-status">
                    {displayStatus}
                </div>
            </div>
          );
    }
}

export default LaundryMachine;