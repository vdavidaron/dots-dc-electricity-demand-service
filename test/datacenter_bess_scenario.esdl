<?xml version='1.0' encoding='UTF-8'?>
<esdl:EnergySystem xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:esdl="http://www.tno.nl/esdl" id="02f37176-6a02-4aeb-8577-1227049648cd" description="Datacenter with BESS and grid connection" name="Datacenter_BESS_Scenario">
  <instance xsi:type="esdl:Instance" name="scenario_instance" id="45f25ed2-4be7-4807-a25a-3b2fdc35f9cd">
    <area xsi:type="esdl:Area" id="0412b52d-5966-40b9-b46f-093d18e9ad12" name="Datacenter_Site">
      <asset xsi:type="esdl:ElectricityNetwork" id="57f765b0-cff4-4ac9-aea9-c7108d83cb16" name="Site LV Network">
        <port xsi:type="esdl:OutPort" id="20bb2bfc-01af-462d-b73a-3c3cdb0f3c90" connectedTo="81878b1b-6ec4-44da-87bf-e49d813b6abd" name="net_to_datacenter"/>
        <port xsi:type="esdl:OutPort" id="a08123a3-a6d4-470c-9d36-4b19c5777b3b" connectedTo="2ab2ec70-5467-4b69-85c5-9cc655db6376" name="net_to_bess"/>
        <port xsi:type="esdl:InPort" id="eda1b73d-6fb2-4577-acd6-18865b2efb84" connectedTo="feecd1cf-c659-48ae-aa2d-a9cb6341c00e" name="net_from_bess"/>
        <port xsi:type="esdl:OutPort" id="5e92fb42-3025-4f2b-98dc-82f9e48a94d1" connectedTo="30e33c20-d823-4afa-b345-97da28ad7b76" name="net_to_grid"/>
        <port xsi:type="esdl:InPort" id="ef381a8c-47e0-4a0c-a18c-378d88a01370" connectedTo="5770d880-6086-4008-854f-72a0a55ad709" name="net_from_grid"/>
      </asset>
      <asset xsi:type="esdl:ElectricityDemand" id="b3640e4a-4465-42b4-84bd-b28db8356477" power="5000.0" name="Datacenter Load">
        <port xsi:type="esdl:InPort" id="81878b1b-6ec4-44da-87bf-e49d813b6abd" connectedTo="20bb2bfc-01af-462d-b73a-3c3cdb0f3c90" name="dc_in"/>
        <costInformation xsi:type="esdl:CostInformation" id="a37fb87a-0489-40f6-b76e-2bce91368d8d">
          <investmentCosts xsi:type="esdl:SingleValue" value="1000000.0"/>
          <fixedMaintenanceCosts xsi:type="esdl:SingleValue" value="50000.0"/>
        </costInformation>
      </asset>
      <asset xsi:type="esdl:Battery" chargeEfficiency="0.95" id="97395372-ee67-42ed-8dd6-bf5600b66225" capacity="2700.0" name="Datacenter BESS" dischargeEfficiency="0.95">
        <port xsi:type="esdl:InPort" id="2ab2ec70-5467-4b69-85c5-9cc655db6376" connectedTo="a08123a3-a6d4-470c-9d36-4b19c5777b3b" name="bess_in"/>
        <port xsi:type="esdl:OutPort" id="feecd1cf-c659-48ae-aa2d-a9cb6341c00e" connectedTo="eda1b73d-6fb2-4577-acd6-18865b2efb84" name="bess_out"/>
        <costInformation xsi:type="esdl:CostInformation" id="1040277b-9390-47fa-8a99-7f5f2a77931c">
          <investmentCosts xsi:type="esdl:SingleValue" value="500000.0"/>
          <fixedMaintenanceCosts xsi:type="esdl:SingleValue" value="20000.0"/>
        </costInformation>
      </asset>
      <asset xsi:type="esdl:PowerPlant" power="20000.0" id="077fc6c5-fac0-4cf2-8ba6-ba62c9359386" name="Grid Connection">
        <port xsi:type="esdl:InPort" id="30e33c20-d823-4afa-b345-97da28ad7b76" connectedTo="5e92fb42-3025-4f2b-98dc-82f9e48a94d1" name="grid_in"/>
        <port xsi:type="esdl:OutPort" id="5770d880-6086-4008-854f-72a0a55ad709" connectedTo="ef381a8c-47e0-4a0c-a18c-378d88a01370" name="grid_out"/>
        <costInformation xsi:type="esdl:CostInformation" id="9ba9f893-d8c4-42e1-89c3-46f5219f9b62">
          <marginalCosts xsi:type="esdl:SingleValue" value="0.2"/>
        </costInformation>
      </asset>
    </area>
  </instance>
</esdl:EnergySystem>
