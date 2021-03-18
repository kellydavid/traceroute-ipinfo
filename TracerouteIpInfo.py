from dataclasses import dataclass, asdict
import requests as req
import json
import gmplot
import sys

IPINFO_TOKEN="insert ipinfo.io token here..."
GOOGLE_MAPS_API_KEY="insert google maps api key here..."

@dataclass
class TrLine:
    hopNumber: int
    hostname: str
    ipAddr: str

    def fromString(str):
        data = str.strip(" ").split(" ")
        if data[0] == "traceroute":
            return None
        if data[2] == "*" or data[3] == "*":
            return None
        else:
            return TrLine(int(data[0]), data[2], data[3].strip("(").strip(")"))

@dataclass
class HostInfo:
    ip: str
    bogon: bool = False
    hostname: str = None
    city: str = None
    region: str = None
    country: str = None
    loc: str = None
    org: str = None
    postal: str = None
    timezone: str = None

    def toCoordinates(self):
        if self.loc != None:
            coords = self.loc.split(",")
            return (float(coords[0]), float(coords[1]))

@dataclass
class IpInfo:
    apiKey: str
    baseUrl: str = "https://ipinfo.io/"

    def batch(self, ips):
        url = f"{self.baseUrl}batch?token={self.apiKey!s}"
        payload = json.dumps(ips)
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        result = req.post(url, data=payload, headers=headers)
        responseData: str = result.text
        return json.loads(responseData)

    def caller(self):
        url = f"{self.baseUrl}?token={self.apiKey!s}"
        result = req.get(url)
        responseData: str = result.text
        return json.loads(responseData)

@dataclass
class TracerouteMapper:
    apiKey: str

    def createGmap(self, coordinate):
        gmap = gmplot.GoogleMapPlotter(coordinate[0], coordinate[1], 5, apikey=self.apiKey)
        return gmap

    def addMarkers(self, gmap, hops):
        for hopNumber in hops.keys():
            hop = hops[hopNumber]
            gmap.marker(hop[0], hop[1], color='cornflowerblue', label=hopNumber, draggable=True)
        return gmap

    def plotCoordinates(self, gmap, coordinates):
        path = zip(*coordinates)
        gmap.plot(*path, edge_width=7, color='red')


    def drawMap(self, hops: dict, mapName: str):
        coordinateList = list(hops.values())
        gmap = self.createGmap(coordinateList[0])
        self.addMarkers(gmap, hops)
        self.plotCoordinates(gmap, coordinateList)
        gmap.draw(f"{mapName}.html")

def parseTraceRoute(trLines):
    output = []
    for line in trLines:
        parsed = TrLine.fromString(line)
        if parsed != None:
            output.append(parsed)
    return output

def mapHop2HostInfo(trLines: list, ipInfoDict: dict):
    result = {}
    for line in trLines:
        ipInfo = ipInfoDict[line.ipAddr]
        hostInfo = HostInfo(**ipInfo)
        result.update({line.hopNumber: hostInfo})
    return result

def getHostInfo(apiKey: str, tracerouteOutput: str):
    rawTrOutput = tracerouteOutput.strip("\n")
    parsed = parseTraceRoute(rawTrOutput.split("\n"))
    ips = []
    for entry in parsed:
        ips.append(entry.ipAddr)
    ipInfo = IpInfo(apiKey)
    mappedResult = {0:HostInfo(**ipInfo.caller())}
    ipinfoResult = ipInfo.batch(ips)
    mappedResult.update(mapHop2HostInfo(parsed, ipinfoResult))
    return mappedResult

def hostInfoAsHopCoordinates(hostInfoDict):
    coordinates = {}
    for key in hostInfoDict.keys():
        entry = hostInfoDict[key].toCoordinates()
        if entry != None:
            coordinates.update({key:entry})
    return coordinates

def printHostInfo(hostInfoDict):
    acc = {}
    for key in hostInfoDict.keys():
        entry = hostInfoDict[key]
        acc.update({key: asdict(entry)})
    result = json.dumps(acc, indent=4)
    print(result)

def main():
    tracerouteOutput = sys.stdin.read()
    sys.stdin.close()
    result = getHostInfo(IPINFO_TOKEN, tracerouteOutput)
    printHostInfo(result)
    coordinates = hostInfoAsHopCoordinates(result)
    TracerouteMapper(GOOGLE_MAPS_API_KEY).drawMap(coordinates, "map")
        
if __name__ == "__main__":
    main()