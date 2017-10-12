import * as React from 'react';
import './StatusBar.css';

export interface StatusBarProps {
    attemptedConnection: boolean;
    washerTimestamp?: number;
    dryerTimestamp?: number;
}

class StatusBar extends React.Component<StatusBarProps, null> {
    
    constructor(props: StatusBarProps) {
        super(props);
    }
    
    render() {
        let status = 'Fetching information...';
        if (this.props.attemptedConnection) {
            if (this.props.washerTimestamp || this.props.dryerTimestamp) {

                let lastUpdatedTimestamp: number = 0;
                if (this.props.washerTimestamp && this.props.dryerTimestamp) {
                    lastUpdatedTimestamp = Math.max(this.props.washerTimestamp, this.props.dryerTimestamp);
                } else if (this.props.washerTimestamp) {
                    lastUpdatedTimestamp = this.props.washerTimestamp;
                } else if (this.props.dryerTimestamp) {
                    lastUpdatedTimestamp = this.props.dryerTimestamp;
                }

                // If timestamp is more than 60 seconds old
                if (Date.now() - lastUpdatedTimestamp > 60000) {
                    let lastUpdatedDate = new Date(lastUpdatedTimestamp);
                    
                    let updatedDateString = (lastUpdatedDate.getMonth() + 1) + '/' + lastUpdatedDate.getDate();
                    let updatedTimeString = (lastUpdatedDate.getHours() + 1).toString();
                    let updatedAMPMString = 'AM';
                    if (lastUpdatedDate.getHours() >= 12) {
                        updatedTimeString = (lastUpdatedDate.getHours() - 12).toString();
                        updatedAMPMString = 'PM';
                    }
                    updatedTimeString += ':';
                    updatedTimeString += lastUpdatedDate.getMinutes() < 10 ? '0' : '';
                    updatedTimeString += lastUpdatedDate.getMinutes();
                    updatedTimeString += ':';
                    updatedTimeString += lastUpdatedDate.getSeconds() < 10 ? '0' : '';
                    updatedTimeString += lastUpdatedDate.getSeconds();
                    updatedTimeString += ' ';
                    updatedTimeString += updatedAMPMString;
    
                    let updatedDateTimeString = updatedDateString + ' ' + updatedTimeString;
                    status = 'Last Updated: ' + updatedDateTimeString;
                } else {
                    let updatedAgoSeconds = Math.round((Date.now() - lastUpdatedTimestamp) / 1000);
                    status = 'Last Updated: ' + updatedAgoSeconds + ' ' +
                             (updatedAgoSeconds === 1 ? 'second' : 'seconds') + 
                             ' ago';
                }
            } else {
                status = 'Failed to get data, retrying...';
            }
        }
        
        return (
            <div className="StatusBar">
                {status}
            </div>
            );
    }
}
    
export default StatusBar;