export interface MockShape {
  name: string;
  direction: "input" | "output";
}

export interface MockCreatorNode {
  creatorClassName: string;
  creatorId: string;
  shapes: MockShape[];
  mockParams: Record<string, unknown>;
  successors?: MockCreatorNode[];
}

export interface MockPlan {
  id: number;
  name: string;
  creators: MockCreatorNode[];
}

export interface MockTemplate {
  id: number;
  name: string;
  creators: MockCreatorNode[];
}

export const MOCK_PLANS: MockPlan[] = [
  {
    id: 1,
    name: "Wing Construction",
    creators: [
      {
        creatorClassName: "VaseModeWingCreator",
        creatorId: "vase_wing",
        shapes: [
          { name: "wing_config", direction: "input" },
          { name: "vase_wing", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
      },
      {
        creatorClassName: "ScaleRotateTranslateCreator",
        creatorId: "mirror_wing",
        shapes: [
          { name: "vase_wing", direction: "input" },
          { name: "mirrored_wing", direction: "output" },
        ],
        mockParams: { loglevel: 50, source_shape: "vase_wing" },
      },
    ],
  },
  {
    id: 2,
    name: "Fuselage Build",
    creators: [
      {
        creatorClassName: "FuselageShellShapeCreator",
        creatorId: "main_fuselage",
        shapes: [
          { name: "fuselage_config", direction: "input" },
          { name: "fuselage_shell", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
      },
    ],
  },
  {
    id: 3,
    name: "Motor Mount",
    creators: [
      {
        creatorClassName: "EngineMountShapeCreator",
        creatorId: "mount_base",
        shapes: [
          { name: "mount_base", direction: "output" },
        ],
        mockParams: { loglevel: 50 },
      },
      {
        creatorClassName: "Cut2ShapesCreator",
        creatorId: "motor_cutout",
        shapes: [
          { name: "mount_base", direction: "input" },
          { name: "motor_cutout", direction: "output" },
        ],
        mockParams: { loglevel: 50, minuend: "mount_base" },
      },
    ],
  },
  {
    id: 4,
    name: "Wing Assembly Pipeline",
    creators: [
      {
        creatorClassName: "VaseModeWingCreator",
        creatorId: "raw_wing",
        shapes: [
          { name: "wing_config", direction: "input" },
          { name: "raw_wing", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
        successors: [
          {
            creatorClassName: "ScaleRotateTranslateCreator",
            creatorId: "positioned_wing",
            shapes: [
              { name: "raw_wing", direction: "input" },
              { name: "positioned_wing", direction: "output" },
            ],
            mockParams: { loglevel: 50, source_shape: "raw_wing" },
            successors: [
              {
                creatorClassName: "Cut2ShapesCreator",
                creatorId: "servo_cutout_left",
                shapes: [
                  { name: "positioned_wing", direction: "input" },
                  { name: "servo_cutout_left", direction: "output" },
                ],
                mockParams: { loglevel: 50 },
              },
              {
                creatorClassName: "Cut2ShapesCreator",
                creatorId: "servo_cutout_right",
                shapes: [
                  { name: "positioned_wing", direction: "input" },
                  { name: "servo_cutout_right", direction: "output" },
                ],
                mockParams: { loglevel: 50 },
              },
              {
                creatorClassName: "SimpleOffsetShapeCreator",
                creatorId: "wing_shell",
                shapes: [
                  { name: "positioned_wing", direction: "input" },
                  { name: "wing_shell", direction: "output" },
                ],
                mockParams: { loglevel: 50 },
                successors: [
                  {
                    creatorClassName: "FuseMultipleShapesCreator",
                    creatorId: "wing_with_servos",
                    shapes: [
                      { name: "wing_shell", direction: "input" },
                      { name: "servo_cutout_left", direction: "input" },
                      { name: "servo_cutout_right", direction: "input" },
                      { name: "wing_with_servos", direction: "output" },
                    ],
                    mockParams: { loglevel: 50 },
                    successors: [
                      {
                        creatorClassName: "RepairFacesShapeCreator",
                        creatorId: "wing_repaired",
                        shapes: [
                          { name: "wing_with_servos", direction: "input" },
                          { name: "wing_repaired", direction: "output" },
                        ],
                        mockParams: { loglevel: 50 },
                        successors: [
                          {
                            creatorClassName: "ExportToStepCreator",
                            creatorId: "wing_step_export",
                            shapes: [
                              { name: "wing_repaired", direction: "input" },
                            ],
                            mockParams: { loglevel: 50, output_dir: "./step" },
                          },
                          {
                            creatorClassName: "ExportToStlCreator",
                            creatorId: "wing_stl_export",
                            shapes: [
                              { name: "wing_repaired", direction: "input" },
                            ],
                            mockParams: { loglevel: 50, output_dir: "./stl" },
                          },
                          {
                            creatorClassName: "ExportTo3mfCreator",
                            creatorId: "wing_3mf_export",
                            shapes: [
                              { name: "wing_repaired", direction: "input" },
                            ],
                            mockParams: { loglevel: 50, output_dir: "./3mf" },
                          },
                        ],
                      },
                    ],
                  },
                ],
              },
            ],
          },
          {
            creatorClassName: "StandWingSegmentOnPrinterCreator",
            creatorId: "print_orientation",
            shapes: [
              { name: "raw_wing", direction: "input" },
              { name: "print_ready_wing", direction: "output" },
            ],
            mockParams: { loglevel: 50 },
            successors: [
              {
                creatorClassName: "ExportToStlCreator",
                creatorId: "print_stl_export",
                shapes: [
                  { name: "print_ready_wing", direction: "input" },
                ],
                mockParams: { loglevel: 50, output_dir: "./print" },
              },
            ],
          },
        ],
      },
      {
        creatorClassName: "WingLoftCreator",
        creatorId: "wing_loft",
        shapes: [
          { name: "wing_config", direction: "input" },
          { name: "wing_loft_solid", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
        successors: [
          {
            creatorClassName: "ServoImporterCreator",
            creatorId: "servo_left",
            shapes: [
              { name: "wing_loft_solid", direction: "input" },
              { name: "servo_left_shape", direction: "output" },
            ],
            mockParams: { loglevel: 50 },
          },
          {
            creatorClassName: "ServoImporterCreator",
            creatorId: "servo_right",
            shapes: [
              { name: "wing_loft_solid", direction: "input" },
              { name: "servo_right_shape", direction: "output" },
            ],
            mockParams: { loglevel: 50 },
          },
          {
            creatorClassName: "ComponentImporterCreator",
            creatorId: "spar_carbon_tube",
            shapes: [
              { name: "wing_loft_solid", direction: "input" },
              { name: "spar_shape", direction: "output" },
            ],
            mockParams: { loglevel: 50 },
          },
        ],
      },
    ],
  },
  {
    id: 5,
    name: "Deep Nesting Stress Test",
    creators: [
      {
        creatorClassName: "VaseModeWingCreator",
        creatorId: "depth_01_wing",
        shapes: [{ name: "depth_01", direction: "output" }],
        mockParams: { loglevel: 50 },
        successors: [
          {
            creatorClassName: "ScaleRotateTranslateCreator",
            creatorId: "depth_02_transform",
            shapes: [{ name: "depth_01", direction: "input" }, { name: "depth_02", direction: "output" }],
            mockParams: { loglevel: 50 },
            successors: [
              {
                creatorClassName: "Cut2ShapesCreator",
                creatorId: "depth_03_cut",
                shapes: [{ name: "depth_02", direction: "input" }, { name: "depth_03", direction: "output" }],
                mockParams: { loglevel: 50 },
                successors: [
                  {
                    creatorClassName: "SimpleOffsetShapeCreator",
                    creatorId: "depth_04_offset",
                    shapes: [{ name: "depth_03", direction: "input" }, { name: "depth_04", direction: "output" }],
                    mockParams: { loglevel: 50 },
                    successors: [
                      {
                        creatorClassName: "FuseMultipleShapesCreator",
                        creatorId: "depth_05_fuse",
                        shapes: [{ name: "depth_04", direction: "input" }, { name: "depth_05", direction: "output" }],
                        mockParams: { loglevel: 50 },
                        successors: [
                          {
                            creatorClassName: "RepairFacesShapeCreator",
                            creatorId: "depth_06_repair",
                            shapes: [{ name: "depth_05", direction: "input" }, { name: "depth_06", direction: "output" }],
                            mockParams: { loglevel: 50 },
                            successors: [
                              {
                                creatorClassName: "ScaleRotateTranslateCreator",
                                creatorId: "depth_07_reposition",
                                shapes: [{ name: "depth_06", direction: "input" }, { name: "depth_07", direction: "output" }],
                                mockParams: { loglevel: 50 },
                                successors: [
                                  {
                                    creatorClassName: "Intersect2ShapesCreator",
                                    creatorId: "depth_08_intersect",
                                    shapes: [{ name: "depth_07", direction: "input" }, { name: "depth_08", direction: "output" }],
                                    mockParams: { loglevel: 50 },
                                    successors: [
                                      {
                                        creatorClassName: "AddMultipleShapesCreator",
                                        creatorId: "depth_09_compound",
                                        shapes: [{ name: "depth_08", direction: "input" }, { name: "depth_09", direction: "output" }],
                                        mockParams: { loglevel: 50 },
                                        successors: [
                                          {
                                            creatorClassName: "ExportToStepCreator",
                                            creatorId: "depth_10_export",
                                            shapes: [{ name: "depth_09", direction: "input" }],
                                            mockParams: { loglevel: 50, output_dir: "./deep" },
                                          },
                                        ],
                                      },
                                    ],
                                  },
                                ],
                              },
                            ],
                          },
                        ],
                      },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
];

export const MOCK_TEMPLATES: MockTemplate[] = [
  {
    id: 101,
    name: "Standard Wing Template",
    creators: [
      {
        creatorClassName: "VaseModeWingCreator",
        creatorId: "vase_wing",
        shapes: [
          { name: "wing_config", direction: "input" },
          { name: "vase_wing", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
      },
      {
        creatorClassName: "ScaleRotateTranslateCreator",
        creatorId: "mirror_wing",
        shapes: [
          { name: "vase_wing", direction: "input" },
          { name: "mirrored_wing", direction: "output" },
        ],
        mockParams: { loglevel: 50, source_shape: "vase_wing" },
      },
    ],
  },
  {
    id: 102,
    name: "Fuselage Pod Template",
    creators: [
      {
        creatorClassName: "FuselageShellShapeCreator",
        creatorId: "pod_body",
        shapes: [
          { name: "fuselage_config", direction: "input" },
          { name: "pod_body", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
      },
    ],
  },
];

export function countCreators(creators: MockCreatorNode[]): number {
  return creators.reduce(
    (sum, c) => sum + 1 + countCreators(c.successors ?? []),
    0,
  );
}
