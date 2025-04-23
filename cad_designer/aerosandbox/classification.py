from cad_designer.airplane.aircraft_topology.models.analysis_model import CnBetaClassification, StabilityLevel, \
    CmAlphaClassification, ClBetaClassification


def classify_Cm_alpha(Cm_alpha: float) -> CmAlphaClassification:
    if Cm_alpha < -0.08:
        return CmAlphaClassification(value=Cm_alpha, classification=StabilityLevel.STRONGLY_STABLE, comment="Excellent restoring moment; very stable in pitch.")
    elif Cm_alpha < -0.04:
        return CmAlphaClassification(value=Cm_alpha, classification=StabilityLevel.MODERATELY_STABLE, comment="Good pitch stability for most aircraft.")
    elif Cm_alpha < -0.005:
        return CmAlphaClassification(value=Cm_alpha, classification=StabilityLevel.MARGINALLY_STABLE, comment="Limited pitch stability; sluggish return to trim.")
    else:
        return CmAlphaClassification(value=Cm_alpha, classification=StabilityLevel.UNSTABLE, comment="Pitch unstable; aircraft diverges from trimmed AoA.")

def classify_Cl_beta(Cl_beta: float) -> ClBetaClassification:
    if Cl_beta > 0.05:
        return ClBetaClassification(value=Cl_beta, classification=StabilityLevel.STRONGLY_STABLE, comment="Excellent roll stability; very responsive.")
    elif Cl_beta > 0.02:
        return ClBetaClassification(value=Cl_beta, classification=StabilityLevel.MODERATELY_STABLE, comment="Sufficient lateral stability for conventional configurations.")
    elif Cl_beta > 0.005:
        return ClBetaClassification(value=Cl_beta, classification=StabilityLevel.MARGINALLY_STABLE, comment="Weak lateral stability; sluggish roll correction.")
    else:
        return ClBetaClassification(value=Cl_beta, classification=StabilityLevel.UNSTABLE, comment="Laterally unstable; aircraft rolls away from level in a sideslip.")

def classify_Cn_beta(Cn_beta: float) -> CnBetaClassification:
    if Cn_beta > 0.09:
        return CnBetaClassification(value=Cn_beta, classification=StabilityLevel.STRONGLY_STABLE, comment="Strong yaw stability; quick heading correction.")
    elif Cn_beta > 0.02:
        return CnBetaClassification(value=Cn_beta, classification=StabilityLevel.MODERATELY_STABLE, comment="Adequate directional stability for general flight.")
    elif Cn_beta > 0.0025:
        return CnBetaClassification(value=Cn_beta, classification=StabilityLevel.MARGINALLY_STABLE, comment="Weak yaw stability; sluggish response to disturbances.")
    else:
        return CnBetaClassification(value=Cn_beta, classification=StabilityLevel.UNSTABLE, comment="Directionally unstable; diverges from intended yaw angle.")

