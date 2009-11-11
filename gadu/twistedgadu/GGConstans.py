#(C) Marek Chrusciel, 
#    Jakub Kosinski, 
#    Marcin Krupowicz,
#    Mateusz Strycharski
#
# $Id: GGConstans.py 56 2008-01-14 13:10:51Z ghandal $

from Helpers import Enum
	
GGPubDirTypes = Enum({
	"Write"       : 0x01,
	"Read"        : 0x02,
	"Search"      : 0x03,
	"SearchReply" : 0x05
	})

GGUserListTypes = Enum({
	"Put"     : 0x00,
	"PutMore" : 0x01,
	"Get"     : 0x02
	})

GGUserListReplyTypes = Enum({
	"PutReply"     : 0x00,
	"PutMoreReply" : 0x01,
	"GetMoreReply" : 0x04,
	"GetReply"     : 0x06
	})
