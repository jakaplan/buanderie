import * as React from 'react';
import './LaundryMachine.css';

export interface LaundryMachineProps {
    name: string;
    draw?: number;
}

class LaundryMachine extends React.Component<LaundryMachineProps, null> {

    constructor(props: LaundryMachineProps) {
        super(props);
    }
    
    render() {
        // Status based on wattage
        let status: string;
        if (this.props.draw === undefined) {
            status = 'Unknown';
        } else if (this.props.draw === 0) {
            status = 'Idle';
        } else {
            status = 'Running';
        }

        // Use the status as the class name to differ the CSS
        let rootClassName: string = 'Laundry-machine ' + status;

        // Only display wattage value if it is known
        let wattageDisplay = '';
        if (this.props.draw) {
            wattageDisplay = this.props.draw / 1000 + 'W';
        }

        return (
            <div className={rootClassName}>
                <div className="Machine-name">
                    {this.props.name}
                </div>
                <div className="Machine-status">
                    Status: {status}
                </div>
                <div className="Machine-wattage">
                    {wattageDisplay}
                </div>
            </div>
          );
    }
}

export default LaundryMachine;