import * as React from 'react';
import './LaundryMachine.css';

export interface LaundryMachineProps {
    name: string;
    image: string;
    draw?: number;
}

class LaundryMachine extends React.Component<LaundryMachineProps, null> {

    constructor(props: LaundryMachineProps) {
        super(props);
    }
    
    render() {
        // Status based on wattage
        let displayStatus: string;
        let cssStatus: string;
        if (this.props.draw === undefined) {
            displayStatus = 'Fetching status...';
            cssStatus = 'draw_unknown';
        } else if (this.props.draw === 0) {
            displayStatus = 'Available';
            cssStatus = 'no_draw';
        } else {
            displayStatus = 'Running';
            cssStatus = 'draw';
        }

        // Use the css status as the class name to change the background color via CSS
        let rootClassName: string = 'Laundry-machine ' + cssStatus;

        // Only display wattage value if it is known
        let wattageDisplay = '';
        if (this.props.draw) {
            wattageDisplay = this.props.draw / 1000 + 'W';

            displayStatus += ' (' + wattageDisplay + ')';
        }

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