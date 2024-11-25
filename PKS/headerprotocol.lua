local headerprotocol = Proto("HeaderProtocol", "Protocol for parsing a custom made header")

-- fields
local f_packet_type = ProtoField.uint8("headerprotocol.packet_type", "Packet Type", base.DEC)
local f_fragment_order = ProtoField.uint32("headerprotocol.fragment_order", "Fragment Order", base.DEC)
local f_next_fragment = ProtoField.uint8("headerprotocol.next_fragment", "Next Fragment", base.HEX)
local f_data_length = ProtoField.uint16("headerprotocol.data_length", "Data Length", base.DEC)
local f_crc = ProtoField.uint16("headerprotocol.crc", "CRC", base.HEX)
local f_data = ProtoField.string("headerprotocol.data", "Data")

-- add fields to protocol
headerprotocol.fields = {
    f_packet_type,
    f_fragment_order,
    f_next_fragment,
    f_data_length,
    f_crc,
    f_data
}

function headerprotocol.dissector(buffer, pinfo, tree)
    -- Check if the buffer is large enough
    if buffer:len() < 10 then return end

    -- Set the protocol column in the packet list
    pinfo.cols.protocol = "MyProtocol"

    -- Create the protocol tree
    local subtree = tree:add(headerprotocol, buffer(), "Custom Protocol Data")

    -- Extract the fields
    local packet_type = buffer(0,1):uint()
    local fragment_order = buffer(1,4):uint()
    local next_fragment = buffer(5,1):uint()
    local data_length = buffer(6,2):uint()
    local crc = buffer(8,2):uint()

    -- Add fields to the tree
    subtree:add(f_packet_type, buffer(0,1))
    subtree:add(f_fragment_order, buffer(1,4))
    subtree:add(f_next_fragment, buffer(5,1))
    subtree:add(f_data_length, buffer(6,2))
    subtree:add(f_crc, buffer(8,2))

    -- Check if there is data to display
    local header_size = 10
    if buffer:len() >= header_size + data_length then
        local data_buffer = buffer(header_size, data_length)
        subtree:add(f_data, data_buffer)
    end

    -- Color-code the packet based on Packet Type
    -- Let's assume Packet Types 2 and 3 carry useful data
    if packet_type == 2 or packet_type == 3 then
        -- Color-code as blue for data messages
        pinfo.cols.info = "Data Message"
        subtree:set_text("Custom Protocol Data Message")
    else
        -- Color-code as green for control messages
        pinfo.cols.info = "Control Message"
        subtree:set_text("Custom Protocol Control Message")
    end
end

-- Register the dissector to specific UDP ports
local udp_port = DissectorTable.get("udp.port")
-- Replace 3000 and 3001 with the ports your protocol uses
udp_port:add(3000, headerprotocol)
udp_port:add(3001, headerprotocol)