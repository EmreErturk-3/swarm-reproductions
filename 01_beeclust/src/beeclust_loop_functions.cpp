#include "beeclust_loop_functions.h"
#include "beeclust_protocol.h"

#include <argos3/core/simulator/simulator.h>
#include <argos3/core/simulator/physics_engine/physics_engine.h>
#include <argos3/plugins/robots/kilobot/control_interface/ci_kilobot_controller.h>
#include <argos3/plugins/robots/kilobot/simulator/kilobot_measures.h>

namespace {

   /*
    * Illuminance field of Bodi et al. (2009), Fig. 4, in patches of the paper's
    * arena: ambient light with a light spot and a shadow spot. Exponential
    * profile fitted to Fig. 4B (scripts/fit_light_field.py, RMSE 2.8 sensor
    * units), clipped to [0, E_max]. The patch size in metres is a parameter.
    */
   const Real AMBIENT_LUX          = 500.0;
   const Real SPOT_LUX             = 731.6;
   const Real MAX_LUX              = 1000.0;
   const Real DECAY_LENGTH_PATCHES = 6.23;
   const Real SPOT_X_PATCHES       = 14.0;

   /* Target zone of the light finders: patches with 600 to 1000 lux (Sec. 2). */
   const Real TARGET_ZONE_LUX = 600.0;

   /* A wall is sensed when it is ahead and within this gap from the body. */
   const Real WALL_SENSING_GAP = 0.005;

}

/****************************************/
/****************************************/

Real CBeeclustLoopFunctions::Illuminance(const CVector2& c_position) const {
   Real fLux = AMBIENT_LUX
      + SPOT_LUX * Exp(-(c_position - m_cLightSpot).Length() / m_fDecayLength)
      - SPOT_LUX * Exp(-(c_position - m_cShadowSpot).Length() / m_fDecayLength);
   return Min(Max(fLux, 0.0), MAX_LUX);
}

/****************************************/
/****************************************/

void CBeeclustLoopFunctions::Init(TConfigurationNode& t_tree) {
   Real fPatch;
   GetNodeAttribute(t_tree, "patch_size", fPatch);
   m_cLightSpot.Set(-SPOT_X_PATCHES * fPatch, 0.0);
   m_cShadowSpot.Set(SPOT_X_PATCHES * fPatch, 0.0);
   m_fDecayLength = DECAY_LENGTH_PATCHES * fPatch;
   GetNodeAttribute(t_tree, "output", m_strOutputPath);
   std::string strMedium;
   GetNodeAttribute(t_tree, "medium", strMedium);
   m_pcMedium = &CSimulator::GetInstance().GetMedium<CKilobotCommunicationMedium>(strMedium);
   m_unTicksPerSecond = static_cast<UInt32>(CPhysicsEngine::GetInverseSimulationClockTick() + 0.5);
   /* The payload of the wall message is unused; the overhead channel needs no CRC. */
   m_tWallMessage = message_t();
   m_tWallMessage.type = BEECLUST_MSG_WALL;
   Reset();
}

/****************************************/
/****************************************/

void CBeeclustLoopFunctions::Reset() {
   /* Kilobot controllers are recreated on reset, so their state pointers change. */
   CollectEntities();
   m_cOutput.close();
   m_cOutput.open(m_strOutputPath, std::ofstream::out | std::ofstream::trunc);
   if(!m_cOutput) {
      THROW_ARGOSEXCEPTION("Cannot open output file \"" << m_strOutputPath << "\"");
   }
   m_cOutput << "time_s,waiting,waiting_in_zone,in_zone,robots" << std::endl;
}

/****************************************/
/****************************************/

void CBeeclustLoopFunctions::Destroy() {
   m_cOutput.close();
}

/****************************************/
/****************************************/

void CBeeclustLoopFunctions::PreStep() {
   for(SRobot& sRobot : m_vecRobots) {
      /*
       * Virtual light sensor, 1 count = 1 lux. The controller copies the ARGoS
       * light sensor into this field only if that sensor is configured, and the
       * experiment file does not configure it.
       */
      sRobot.Controller->GetRobotState()->ambientlight =
         static_cast<SInt16>(Illuminance(Position(*sRobot.Entity)));
      /* Virtual wall sensor; a NULL message clears it. */
      m_pcMedium->SendOHCMessageTo(*sRobot.Entity,
                                   IsFacingWall(*sRobot.Entity) ? &m_tWallMessage : nullptr);
   }
}

/****************************************/
/****************************************/

void CBeeclustLoopFunctions::PostStep() {
   UInt32 unTick = GetSpace().GetSimulationClock();
   if(unTick % m_unTicksPerSecond != 0) return;
   UInt32 unWaiting = 0;
   UInt32 unInZone = 0;
   UInt32 unWaitingInZone = 0;
   for(SRobot& sRobot : m_vecRobots) {
      bool bWaiting = (sRobot.Controller->GetRobotState()->color == BEECLUST_COLOR_WAITING);
      bool bInZone = (Illuminance(Position(*sRobot.Entity)) >= TARGET_ZONE_LUX);
      unWaiting += bWaiting;
      unInZone += bInZone;
      unWaitingInZone += (bWaiting && bInZone);
   }
   m_cOutput << unTick / m_unTicksPerSecond << ','
             << unWaiting << ','
             << unWaitingInZone << ','
             << unInZone << ','
             << m_vecRobots.size() << '\n';
}

/****************************************/
/****************************************/

CColor CBeeclustLoopFunctions::GetFloorColor(const CVector2& c_position) {
   UInt8 unGrey = static_cast<UInt8>(255.0 * Illuminance(c_position) / MAX_LUX);
   return CColor(unGrey, unGrey, unGrey);
}

/****************************************/
/****************************************/

void CBeeclustLoopFunctions::CollectEntities() {
   m_vecRobots.clear();
   for(auto& tEntry : GetSpace().GetEntitiesByType("kilobot")) {
      CKilobotEntity* pcRobot = any_cast<CKilobotEntity*>(tEntry.second);
      m_vecRobots.push_back(SRobot{
         pcRobot,
         &dynamic_cast<CCI_KilobotController&>(pcRobot->GetControllableEntity().GetController())
      });
   }
   m_vecWalls.clear();
   for(auto& tEntry : GetSpace().GetEntitiesByType("box")) {
      m_vecWalls.push_back(any_cast<CBoxEntity*>(tEntry.second));
   }
}

/****************************************/
/****************************************/

CVector2 CBeeclustLoopFunctions::Heading(CKilobotEntity& c_robot) {
   CRadians cYaw, cPitch, cRoll;
   c_robot.GetEmbodiedEntity().GetOriginAnchor().Orientation.ToEulerAngles(cYaw, cPitch, cRoll);
   return CVector2(1.0, cYaw);
}

/****************************************/
/****************************************/

CVector2 CBeeclustLoopFunctions::Position(CKilobotEntity& c_robot) {
   /* The origin anchor lies on the leg axis, KILOBOT_ECCENTRICITY behind the body centre. */
   const CVector3& cOrigin = c_robot.GetEmbodiedEntity().GetOriginAnchor().Position;
   return CVector2(cOrigin.GetX(), cOrigin.GetY()) + KILOBOT_ECCENTRICITY * Heading(c_robot);
}

/****************************************/
/****************************************/

bool CBeeclustLoopFunctions::IsFacingWall(CKilobotEntity& c_robot) const {
   const CVector2 cHeading = Heading(c_robot);
   const CVector2 cPosition = Position(c_robot);
   for(CBoxEntity* pcWall : m_vecWalls) {
      /* Closest point of the wall footprint; walls are axis-aligned boxes. */
      const CVector3& cCentre = pcWall->GetEmbodiedEntity().GetOriginAnchor().Position;
      const CVector3& cSize = pcWall->GetSize();
      CVector2 cClosest(
         Min(Max(cPosition.GetX(), cCentre.GetX() - 0.5 * cSize.GetX()), cCentre.GetX() + 0.5 * cSize.GetX()),
         Min(Max(cPosition.GetY(), cCentre.GetY() - 0.5 * cSize.GetY()), cCentre.GetY() + 0.5 * cSize.GetY()));
      CVector2 cToWall = cClosest - cPosition;
      if(cToWall.Length() <= KILOBOT_RADIUS + WALL_SENSING_GAP &&
         cToWall.DotProduct(cHeading) > 0.0) {
         return true;
      }
   }
   return false;
}

/****************************************/
/****************************************/

REGISTER_LOOP_FUNCTIONS(CBeeclustLoopFunctions, "beeclust_loop_functions")
