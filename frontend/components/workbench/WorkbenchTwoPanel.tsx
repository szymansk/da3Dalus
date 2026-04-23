import React from "react";

interface WorkbenchTwoPanelProps {
  leftWidth?: number;
  children: React.ReactNode;
  className?: string;
}

export function WorkbenchTwoPanel({ leftWidth = 360, children, className }: Readonly<WorkbenchTwoPanelProps>) {
  const childArray = React.Children.toArray(children);
  return (
    <div className={`flex h-full min-h-0 flex-1 gap-4 overflow-hidden${className ? ` ${className}` : ""}`}>
      <div style={{ width: leftWidth, minWidth: leftWidth }} className="flex min-h-0 shrink-0 flex-col overflow-hidden">
        {childArray[0]}
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {childArray[1]}
      </div>
    </div>
  );
}
