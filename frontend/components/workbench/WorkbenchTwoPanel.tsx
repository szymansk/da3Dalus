import React from "react";

interface WorkbenchTwoPanelProps {
  leftWidth?: number;
  children: React.ReactNode;
  className?: string;
}

export function WorkbenchTwoPanel({ leftWidth = 360, children, className }: WorkbenchTwoPanelProps) {
  const childArray = React.Children.toArray(children);
  return (
    <div className={`flex flex-1 gap-4 overflow-hidden${className ? ` ${className}` : ""}`}>
      <div style={{ width: leftWidth, minWidth: leftWidth }} className="shrink-0 overflow-hidden">
        {childArray[0]}
      </div>
      <div className="flex-1 overflow-hidden">
        {childArray[1]}
      </div>
    </div>
  );
}
